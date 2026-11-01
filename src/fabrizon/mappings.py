"""Reader for Tiny v1 and Tiny v2 mapping files (Yarn, Fabric intermediary, Mojang-via-Tiny).

Stage 2, piece 1. Turns intermediary names (class_1234, method_5678) into readable names
so they can be matched against Horizon's Rust source.
"""

from __future__ import annotations

import gzip
import os
from dataclasses import dataclass, field


class MappingError(ValueError):
    pass


def _unescape(s: str) -> str:
    return (s.replace("\\\\", "\x00").replace("\\n", "\n").replace("\\t", "\t")
            .replace("\\r", "\r").replace("\\0", "\0").replace("\x00", "\\"))


@dataclass
class Mappings:
    namespaces: list[str]
    # per namespace index: class names; entries are tuples of names across all namespaces
    classes: list[tuple[str, ...]] = field(default_factory=list)
    # (owner in ns0, desc in ns0, names...)
    methods: list[tuple[str, str, tuple[str, ...]]] = field(default_factory=list)
    fields: list[tuple[str, str, tuple[str, ...]]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._cls_idx: list[dict[str, tuple[str, ...]]] | None = None
        self._m_idx: dict[tuple[int, str], list[tuple[str, str, tuple[str, ...]]]] | None = None

    def _ns(self, ns: str) -> int:
        try:
            return self.namespaces.index(ns)
        except ValueError:
            raise MappingError(f"namespace {ns!r} not in {self.namespaces}") from None

    def _build(self) -> None:
        self._cls_idx = [{} for _ in self.namespaces]
        for c in self.classes:
            for i, n in enumerate(c):
                if n:
                    self._cls_idx[i][n] = c
        self._m_idx = {}
        for m in self.methods:
            for i, n in enumerate(m[2]):
                if n:
                    self._m_idx.setdefault((i, n), []).append(m)

    def map_class(self, name: str, to_ns: str, from_ns: str | None = None) -> str | None:
        """Map an internal class name (a/b/C). Searches every namespace unless from_ns is given."""
        if self._cls_idx is None:
            self._build()
        name = name.replace(".", "/")
        dst = self._ns(to_ns)
        srcs = [self._ns(from_ns)] if from_ns else range(len(self.namespaces))
        for i in srcs:
            c = self._cls_idx[i].get(name)
            if c and c[dst]:
                return c[dst]
        return None

    def map_methods(self, name: str, to_ns: str, owner: str | None = None) -> list[str]:
        """Map a method name to to_ns. Methods with the same name on different owners can differ,
        so pass the owner (in any namespace) when you have it."""
        if self._m_idx is None:
            self._build()
        dst = self._ns(to_ns)
        owner_names: set[str] | None = None
        if owner:
            o = owner.replace(".", "/")
            owner_names = {o}
            for i in range(len(self.namespaces)):
                c = self._cls_idx[i].get(o)
                if c:
                    owner_names.update(x for x in c if x)
        out: list[str] = []
        for i in range(len(self.namespaces)):
            for m_owner, _desc, names in self._m_idx.get((i, name), []):
                if owner_names is not None:
                    c = self._cls_idx[0].get(m_owner)
                    cand = {m_owner} | ({x for x in c if x} if c else set())
                    if not (cand & owner_names):
                        continue
                if names[dst] and names[dst] not in out:
                    out.append(names[dst])
        return out


def parse_tiny(text: str) -> Mappings:
    lines = text.splitlines()
    if not lines:
        raise MappingError("empty mappings file")
    head = lines[0].split("\t")
    if head[0] == "v1":
        return _parse_v1(head[1:], lines[1:])
    if head[0] == "tiny" and len(head) >= 5 and head[1] == "2":
        return _parse_v2(head[3:], lines[1:])
    raise MappingError("not a Tiny v1 or v2 file (header must start with 'v1' or 'tiny\\t2')")


def _parse_v1(ns: list[str], lines: list[str]) -> Mappings:
    m = Mappings(namespaces=ns)
    n = len(ns)
    for ln in lines:
        if not ln.strip() or ln.startswith("#"):
            continue
        p = [_unescape(x) for x in ln.split("\t")]
        kind = p[0]
        if kind == "CLASS" and len(p) == 1 + n:
            m.classes.append(tuple(p[1:]))
        elif kind in ("METHOD", "FIELD") and len(p) == 3 + n:
            (m.methods if kind == "METHOD" else m.fields).append((p[1], p[2], tuple(p[3:])))
    return m


def _parse_v2(ns: list[str], lines: list[str]) -> Mappings:
    m = Mappings(namespaces=ns)
    n = len(ns)
    cur: tuple[str, ...] | None = None
    for ln in lines:
        if not ln.strip() or ln.startswith("#"):
            continue
        depth = len(ln) - len(ln.lstrip("\t"))
        p = [_unescape(x) for x in ln.lstrip("\t").split("\t")]
        if depth == 0 and p[0] == "c":
            names = p[1:1 + n] + [""] * max(0, n - len(p[1:1 + n]))
            cur = tuple(names)
            m.classes.append(cur)
        elif depth == 1 and cur is not None and p[0] in ("m", "f"):
            desc = p[1]
            names = p[2:2 + n] + [""] * max(0, n - len(p[2:2 + n]))
            (m.methods if p[0] == "m" else m.fields).append((cur[0], desc, tuple(names)))
        # depth >= 2 (parameters, locals) and comments (c) are ignored
    return m


def load_tiny(path: str) -> Mappings:
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return parse_tiny(f.read())
    with open(path, encoding="utf-8") as f:
        return parse_tiny(f.read())


def get_cached_mappings_dir() -> str:
    path = os.path.join(os.path.expanduser("~"), ".fabrizon", "mappings")
    os.makedirs(path, exist_ok=True)
    return path


def extract_mc_version(ver: str | None) -> str:
    if not ver:
        return "26.3"
    import re
    m = re.search(r"(\d+(?:\.\d+)+)", str(ver))
    return m.group(1) if m else "26.3"


def ensure_mappings(mc_version: str | None = None) -> tuple[str, Mappings]:
    """Auto-detect, download or retrieve cached Yarn mappings for a Minecraft version.
    Returns (source_description, Mappings).
    """
    import io
    import json
    import os
    import urllib.request
    import zipfile

    ver = extract_mc_version(mc_version)
    cache_dir = get_cached_mappings_dir()

    # 1. Check exact version cached
    v_path = os.path.join(cache_dir, f"yarn-{ver}.tiny")
    if os.path.isfile(v_path):
        return (f"cached {os.path.basename(v_path)}", load_tiny(v_path))

    # 2. Check local fallback paths (e.g. temp from previous session or default)
    temp_tiny = r"C:\Users\sesed\AppData\Local\Temp\opencode\hz\yarn.tiny"
    if os.path.isfile(temp_tiny):
        try:
            m = load_tiny(temp_tiny)
            try:
                import shutil
                shutil.copyfile(temp_tiny, v_path)
            except Exception:
                pass
            return ("local yarn.tiny", m)
        except Exception:
            pass

    # 3. Check any existing cached .tiny in cache_dir
    cached_files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith(".tiny")]
    if cached_files:
        return (f"cached {os.path.basename(cached_files[0])}", load_tiny(cached_files[0]))

    # 4. Try downloading from Fabric Meta API
    for try_ver in (ver, "1.21"):
        try:
            req = urllib.request.Request(
                f"https://meta.fabricmc.net/v2/versions/yarn/{try_ver}",
                headers={"User-Agent": "Fabrizon/1.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                if data and isinstance(data, list) and "version" in data[0]:
                    yarn_v = data[0]["version"]
                    jar_url = f"https://maven.fabricmc.net/net/fabricmc/yarn/{yarn_v}/yarn-{yarn_v}-v2.jar"
                    jreq = urllib.request.Request(jar_url, headers={"User-Agent": "Fabrizon/1.0"})
                    with urllib.request.urlopen(jreq, timeout=12) as jresp:
                        with zipfile.ZipFile(io.BytesIO(jresp.read())) as jzf:
                            tiny_content = jzf.read("mappings/mappings.tiny").decode("utf-8")
                            with open(v_path, "w", encoding="utf-8") as out:
                                out.write(tiny_content)
                            return (f"Yarn {yarn_v} (downloaded)", parse_tiny(tiny_content))
        except Exception:
            pass

    raise MappingError(f"could not automatically download or locate Yarn mappings for Minecraft {ver}. Please specify a mappings file.")
