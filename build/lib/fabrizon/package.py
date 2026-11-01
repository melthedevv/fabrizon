"""Stage 5: package a generated bundle as a deterministic `.hnmod`.

Format source: horizon-mods `native/tools/native.py` (`package`) and the registry's
native-mod rules. A `.hnmod` is a zip with

    horizon-native.json          {"schema": 1, "id", "version", "game",
                                  "horizon", "mixins", "hooks"}
    mixins/<id>/horizon-mixin.toml
    mixins/<id>/*.rs

and nothing else: `NOTICE.md`, `TODO.md` and `BRIEF.md` are working notes for the
person finishing the port, not part of the mod. The archive is byte-for-byte
reproducible (sorted entries, fixed timestamp, fixed mode), so the registry's
SHA-256 check is stable.

Nothing here executes the bundle. It only reads files, checks the pinned revisions
and writes a zip.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from dataclasses import dataclass

MAX_FILES = 512
MAX_BYTES = 64 * 1024 * 1024
FIXED_DATE = (2026, 1, 1, 0, 0, 0)
MOD_ID = re.compile(r"^[a-z0-9_]+$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")

# crates/horizon-client/src/game/native_hooks.rs, as horizon-mods reads it.
HOOKS_FILE = "crates/horizon-client/src/game/native_hooks.rs"
HOOKS_LINE = re.compile(r"^pub\(crate\) const NATIVE_HOOKS_API: u32 = (\d+);$", re.M)


class PackageError(ValueError):
    """The bundle or the compatibility data cannot be packaged as-is."""


@dataclass
class Packed:
    path: str
    size: int
    sha256: str

    def to_dict(self) -> dict:
        return {"file": self.path, "size": self.size, "sha256": self.sha256}


def _unescape(s: str) -> str:
    return (s.replace("\\\\", "\x00").replace('\\"', '"').replace("\\n", "\n")
            .replace("\\t", "\t").replace("\x00", "\\"))


def read_toml_strings(text: str) -> dict[str, dict[str, str]]:
    """The simple `key = "string"` entries of each table, without a TOML dependency.

    Only the three fields packaging needs (`[mod] id`/`version`, `[compatibility]
    horizon_revision`) are strings; everything else is ignored.
    """
    out: dict[str, dict[str, str]] = {}
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[[") and line.endswith("]]"):
            section = line[2:-2].strip() + "[]"
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            out.setdefault(section, {})
            continue
        m = re.match(r'^([A-Za-z0-9_-]+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', line)
        if m and section:
            out.setdefault(section, {})[m.group(1)] = _unescape(m.group(2))
    return out


def hooks_api(horizon_dir: str) -> int | None:
    """The `NATIVE_HOOKS_API` of a Horizon checkout, or None when it has no hook file."""
    path = os.path.join(horizon_dir, *HOOKS_FILE.split("/"))
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    found = HOOKS_LINE.search(text)
    return int(found.group(1)) if found else None


def load_compatibility(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as e:
        raise PackageError(f"cannot read compatibility file: {e}") from e
    except json.JSONDecodeError as e:
        raise PackageError(f"compatibility file is not JSON: {e}") from e
    if not isinstance(data, dict):
        raise PackageError("compatibility file must be a JSON object")
    return data


def build_compatibility(horizon_dir: str | None = None, *, game: str | None = None,
                        horizon_revision: str | None = None,
                        mixins_revision: str | None = None, hooks: int | None = None,
                        base: dict | None = None) -> dict:
    """Merge explicit values over a compatibility.json and a Horizon checkout.

    Anything still unknown stays missing: packaging fails rather than inventing a
    revision, a game version or a hook-point level.
    """
    compat = dict(base or {})
    if game:
        compat["game"] = game
    if horizon_revision:
        compat["horizon_revision"] = horizon_revision
    if mixins_revision:
        compat["horizon_mixins_revision"] = mixins_revision
    if hooks is not None:
        compat["hooks"] = hooks
    elif compat.get("hooks") is None and horizon_dir:
        found = hooks_api(horizon_dir)
        if found is not None:
            compat["hooks"] = found
    compat.setdefault("horizon_repository", "https://github.com/horizon-rust/horizon")
    compat.setdefault("horizon_mixins_repository", "https://github.com/horizon-rust/horizon-mixins")
    return compat


def _manifest(bundle_dir: str) -> tuple[dict[str, dict[str, str]], str]:
    toml_path = os.path.join(bundle_dir, "horizon-mixin.toml")
    try:
        with open(toml_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        raise PackageError(f"not a horizon-mixins bundle (no horizon-mixin.toml): {e}") from e
    return read_toml_strings(text), text


def package_bundle(bundle_dir: str, out_path: str, compat: dict,
                   mod_id: str | None = None, version: str | None = None) -> Packed:
    """Write `<out_path>` for the bundle in `bundle_dir`; return its size and SHA-256."""
    tables, _ = _manifest(bundle_dir)
    mod = tables.get("mod", {})
    mid = mod_id or mod.get("id", "")
    ver = version or mod.get("version", "")
    if not MOD_ID.match(mid or ""):
        raise PackageError(f"mod id {mid!r} must match [a-z0-9_]+ (the registry's rule)")
    if not ver or any(c in ver for c in '\\/:*?"<>|'):
        raise PackageError(f"mod version {ver!r} is empty or not a plain filename component")

    horizon = compat.get("horizon_revision") or ""
    mixins = compat.get("horizon_mixins_revision") or ""
    game = compat.get("game") or ""
    hooks = compat.get("hooks")
    if not SHA1.match(horizon):
        raise PackageError("compatibility.horizon_revision must be an exact 40-character commit")
    if not SHA1.match(mixins):
        raise PackageError("compatibility.horizon_mixins_revision must be an exact 40-character commit")
    if not game:
        raise PackageError("compatibility.game is required (the Minecraft version the build targets)")
    if not isinstance(hooks, int) or isinstance(hooks, bool) or hooks < 0:
        raise PackageError("compatibility.hooks must be a non-negative integer (NATIVE_HOOKS_API)")

    pinned = tables.get("compatibility", {}).get("horizon_revision")
    if pinned and pinned != horizon:
        raise PackageError(
            f"horizon-mixin.toml pins horizon_revision {pinned}, compatibility says {horizon}; "
            "they must match or the launcher builds an unverified game"
        )

    manifest = {
        "schema": 1,
        "id": mid,
        "version": ver,
        "game": game,
        "horizon": horizon,
        "mixins": mixins,
        "hooks": hooks,
    }
    files: dict[str, bytes] = {
        "horizon-native.json": (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    }
    try:
        names = sorted(os.listdir(bundle_dir))
    except OSError as e:
        raise PackageError(f"cannot list bundle: {e}") from e
    for name in names:
        full = os.path.join(bundle_dir, name)
        if not os.path.isfile(full) or os.path.splitext(name)[1] not in (".rs", ".toml"):
            continue
        with open(full, "rb") as fh:
            files[f"mixins/{mid}/{name}"] = fh.read()

    if len(files) > MAX_FILES:
        raise PackageError(f"{len(files)} files exceeds the registry limit of {MAX_FILES}")
    total = sum(len(v) for v in files.values())
    if total > MAX_BYTES:
        raise PackageError(f"{total} bytes exceeds the registry limit of {MAX_BYTES}")

    out_path = os.path.abspath(out_path)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)

    with open(out_path, "rb") as fh:
        data = fh.read()
    return Packed(out_path, len(data), hashlib.sha256(data).hexdigest())


def read_packed(path: str) -> dict:
    """Read back a `.hnmod` for tests and for `fabrizon package --inspect`."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read("horizon-native.json"))
    return {"manifest": manifest, "names": names}
