"""Index of Rust functions in a Horizon checkout.

Stage 2, piece 2. Scans .rs files and records every `fn` with its module path and,
if it sits in an impl block, the type (and trait) it belongs to, plus its parameter
list and return type so later stages can emit typed helper bindings. This is a
lightweight lexical scan, not a compiler: macros, generated code and cfg-gated
items can be missed. Treat results as candidates to verify against the pinned source.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Param:
    name: str
    ty: str

    @property
    def is_self(self) -> bool:
        return self.name == "self"


@dataclass(frozen=True)
class RustFn:
    name: str
    module: str          # e.g. "server::tick"
    impl_type: str | None
    trait: str | None
    file: str
    line: int
    params: tuple[Param, ...] = ()
    ret: str | None = None       # None for unit
    is_pub: bool = False
    crate: str = ""              # Cargo package name, e.g. "horizon-core"
    generic: bool = False        # generic params or a `where` clause
    is_async: bool = False
    is_unsafe: bool = False
    is_const: bool = False
    impl_generic: bool = False   # `impl<T> Type<T>`: the target type is generic
    doc: str = ""                # the `///` comment block directly above
    identity: str = ""           # horizon-mixins' impl identity, e.g. "GameLevel<'_>"

    @property
    def hookable(self) -> bool:
        """horizon-mixins rejects generic, const, unsafe and async targets."""
        return not (self.generic or self.impl_generic or self.is_async or self.is_unsafe or self.is_const)

    @property
    def arity(self) -> int:
        return len([p for p in self.params if not p.is_self])

    @property
    def path(self) -> str:
        if self.impl_type:
            base = f"{self.module}::{self.impl_type}" if self.module else self.impl_type
            return f"{base}::{self.name}"
        return f"{self.module}::{self.name}" if self.module else self.name

    @property
    def target_path(self) -> str:
        """The ID horizon-mixins assigns: module path, impl identity, fn name."""
        if self.identity:
            return f"{self.module}::{self.identity}::{self.name}" if self.module else f"{self.identity}::{self.name}"
        return self.path

    @property
    def target(self) -> str:
        """Full horizon-mixins target ID, or "" when the crate name is unknown."""
        return f"{self.crate}::{self.target_path}" if self.crate else ""

    @property
    def signature(self) -> str:
        args = ", ".join(p.ty if p.is_self else f"{p.name}: {p.ty}" for p in self.params)
        return f"fn {self.name}({args})" + (f" -> {self.ret}" if self.ret else "")

    def param(self, name: str) -> Param | None:
        for p in self.params:
            if p.name == name:
                return p
        return None


_FN = re.compile(r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)")
_MOD = re.compile(r"\bmod\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
_IMPL = re.compile(r"\bimpl\b([^{;]*)\{")
_TYPE_NAME = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:<[^{]*)?$")


def _strip(src: str) -> str:
    """Blank out comments and string/char literals, keeping line structure."""
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i)); i = j
        elif src.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if src.startswith("/*", j): depth += 1; j += 2
                elif src.startswith("*/", j): depth -= 1; j += 2
                else: j += 1
            out.append("".join(ch if ch == "\n" else " " for ch in src[i:j])); i = j
        elif c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out.append("".join(ch if ch == "\n" else " " for ch in src[i:j])); i = j
        else:
            out.append(c); i += 1
    return "".join(out)


def _file_module(rel: str) -> str:
    # Normalise separators: callers pass paths from either platform convention.
    parts = rel[:-3].replace("\\", "/").split("/")
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] in ("lib", "main", "mod"):
        parts = parts[:-1]
    return "::".join(parts)


_CRATE_NAME = re.compile(r'^\s*name\s*=\s*"([^"]+)"', re.M)


def _toml_array(text: str, key: str) -> list[str]:
    """Values of a simple `key = ["a", "b"]` array in a Cargo.toml table body."""
    m = re.search(rf"^\s*{re.escape(key)}\s*=\s*\[(.*?)\]", text, re.M | re.S)
    if not m:
        return []
    return re.findall(r'"([^"]*)"', m.group(1))


def _package_tables(text: str) -> dict[str, str]:
    """Split a Cargo.toml into `table name -> body` (only `[...]` tables, not `[[...]]`)."""
    out: dict[str, str] = {}
    for m in re.finditer(r"^\[([^\[\]\n]+)\](.*?)(?=^\[|\Z)", text, re.M | re.S):
        out[m.group(1).strip()] = m.group(2)
    return out


def _crate_name(cargo_toml: str) -> str | None:
    """The cargo *target* name (lib name when set), dashes normalised to underscores.

    horizon-mixins builds target IDs from `cargo_metadata`'s target name, which is the
    `[lib] name` when present and the package name otherwise.
    """
    try:
        with open(cargo_toml, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    tables = _package_tables(text)
    lib = tables.get("lib")
    if lib:
        n = _CRATE_NAME.search(lib)
        if n:
            return n.group(1).replace("-", "_")
    pkg = tables.get("package")
    if pkg:
        n = _CRATE_NAME.search(pkg)
        if n:
            return n.group(1).replace("-", "_")
    return None


def _workspace_members(root: str) -> set[str] | None:
    """Absolute member directories of the workspace at `root`, or None when it is not one."""
    cargo = os.path.join(root, "Cargo.toml")
    try:
        with open(cargo, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    tables = _package_tables(text)
    body = tables.get("workspace")
    if body is None:
        return None
    import glob

    members: set[str] = set()
    for pattern in _toml_array(body, "members"):
        for hit in glob.glob(os.path.join(root, pattern)):
            if os.path.isdir(hit):
                members.add(os.path.normcase(os.path.abspath(hit)))
    for pattern in _toml_array(body, "exclude"):
        for hit in glob.glob(os.path.join(root, pattern)):
            members.discard(os.path.normcase(os.path.abspath(hit)))
    if "package" in tables:  # the workspace root can be a package too
        members.add(os.path.normcase(os.path.abspath(root)))
    return members


def _crate_root(path: str, cache: dict[str, tuple[str, str] | None]) -> tuple[str, str] | None:
    """Nearest ancestor with a Cargo.toml that names a package -> (dir, crate name)."""
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if d in cache:
            return cache[d]
        cargo = os.path.join(d, "Cargo.toml")
        if os.path.isfile(cargo):
            name = _crate_name(cargo)
            if name:
                cache[d] = (d, name)
                return cache[d]
        parent = os.path.dirname(d)
        if parent == d:
            cache[d] = None
            return None
        d = parent


def _norm_type(text: str) -> str:
    """Normalise a type the way horizon-mixins does for IDs: no spaces, lifetimes -> '_."""
    t = re.sub(r"\s+", "", text)
    return re.sub(
        r"'([A-Za-z_][A-Za-z0-9_]*)",
        lambda m: "'static" if m.group(1) == "static" else "'_",
        t,
    )


def _split_where(text: str) -> str:
    """Cut a top-level `where` clause off an impl header."""
    depth = 0
    for i, ch in enumerate(text):
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth -= 1
        elif depth == 0 and text.startswith("where", i):
            before = text[i - 1] if i else " "
            after = text[i + 5] if i + 5 < len(text) else " "
            if not before.isalnum() and not after.isalnum():
                return text[:i]
    return text


def _simple_type(text: str) -> str | None:
    t = text.strip().lstrip("&").removeprefix("mut ").strip()
    m = re.match(r"(?:[A-Za-z_][A-Za-z0-9_]*::)*([A-Za-z_][A-Za-z0-9_]*)", t)
    return m.group(1) if m else None


def _impl_header(rest: str) -> tuple[str | None, str | None, bool, str]:
    """Parse an impl header -> (type name, trait name, generic, identity)."""
    raw = _split_where(rest.split("{")[0]).strip()
    generic = bool(re.match(r"^<", raw))
    body = raw
    if generic:  # skip `impl<T: Bound>`
        depth = 0
        for i, ch in enumerate(body):
            if ch == "<":
                depth += 1
            elif ch == ">":
                depth -= 1
                if depth == 0:
                    body = body[i + 1 :].strip()
                    break
    if " for " in body:
        trait_text, self_text = body.split(" for ", 1)
        return (_simple_type(self_text), _simple_type(trait_text), generic,
                f"<{_norm_type(self_text)} as {_norm_type(trait_text)}>")
    return _simple_type(body), None, generic, _norm_type(body)


def _split_top(text: str, sep: str = ",") -> list[str]:
    """Split on `sep` at nesting depth 0 for <> () [] {}."""
    out, depth, cur = [], 0, []
    for ch in text:
        if ch in "<([{":
            depth += 1
        elif ch in ">)]}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur))
    return out


def _split_param(text: str) -> tuple[str, str] | None:
    """Split `name: Type` on the first single `:` at nesting depth 0 (not `::`)."""
    depth = 0
    for i, ch in enumerate(text):
        if ch in "<([{":
            depth += 1
        elif ch in ">)]}":
            depth -= 1
        elif ch == ":" and depth == 0:
            if (i + 1 < len(text) and text[i + 1] == ":") or (i and text[i - 1] == ":"):
                continue
            name = text[:i].strip().removeprefix("mut ").strip()
            ty = text[i + 1 :].strip()
            return (name, ty) if name and ty else None
    return None


def _signature(text: str, after_name: int) -> tuple[tuple[Param, ...], str | None, bool]:
    """Parse `(params) -> ret` starting just after the fn name. Third value: generic."""
    i, n = after_name, len(text)
    generic = False
    while i < n and text[i] not in "(<":
        if text[i] in "{;":
            return (), None, False
        i += 1
    if i < n and text[i] == "<":  # generic parameters
        generic = True
        depth = 0
        while i < n:
            if text[i] == "<":
                depth += 1
            elif text[i] == ">":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        while i < n and text[i] != "(":
            if text[i] in "{;":
                return (), None, generic
            i += 1
    if i >= n or text[i] != "(":
        return (), None, generic
    start = i + 1
    depth = 1
    i += 1
    while i < n and depth:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
        i += 1
    params_text = text[start : i - 1]
    params: list[Param] = []
    for raw in _split_top(params_text):
        p = raw.strip()
        if not p:
            continue
        if p in ("self", "&self", "&mut self", "mut self"):
            params.append(Param("self", p))
            continue
        parts = _split_param(p)
        if parts is None:
            params.append(Param(p, ""))
            continue
        name, ty = parts
        params.append(Param(name, ty))
    # return type
    j = i
    while j < n and text[j] in " \t\r\n":
        j += 1
    ret = None
    if text.startswith("->", j):
        k = j + 2
        depth = 0
        while k < n:
            ch = text[k]
            if ch in "<([":
                depth += 1
            elif ch in ">)]":
                depth -= 1
            elif ch in "{;" and depth == 0:
                break
            k += 1
        ret = text[j + 2 : k].strip()
        if re.search(r"\bwhere\b", ret):
            generic = True
            ret = re.split(r"\s+where\s+", ret)[0].strip()
        if ret in ("", "()"):
            ret = None
    return tuple(params), ret, generic


def _doc_above(lines: list[str], lineno: int) -> str:
    """The `///` / `//` comment block immediately above 1-based `lineno`, joined."""
    out: list[str] = []
    i = lineno - 2
    while i >= 0:
        s = lines[i].strip()
        if s.startswith("///") or s.startswith("//!"):
            out.append(s[3:].strip())
        elif s.startswith("//"):
            out.append(s[2:].strip())
        elif s.startswith("#["):  # attributes may sit between the doc and the item
            pass
        else:
            break
        i -= 1
    return " ".join(reversed(out))


def index_source(src: str, rel_path: str, crate: str = "") -> list[RustFn]:
    base_mod = _file_module(rel_path)
    clean = _strip(src)
    src_lines = src.split("\n")
    line_starts = [0]
    for i, ch in enumerate(clean):
        if ch == "\n":
            line_starts.append(i + 1)
    fns: list[RustFn] = []
    # stack of (kind, value, depth_at_open)
    stack: list[tuple[str, tuple, int]] = []
    depth = 0
    for lineno, line in enumerate(clean.split("\n"), 1):
        headers: dict[int, tuple[str, tuple]] = {}
        for m in _MOD.finditer(line):
            headers[m.end() - 1] = ("mod", (m.group(1),))
        for m in _IMPL.finditer(line):
            headers[m.end() - 1] = ("impl", _impl_header(m.group(1)))
        fn_at = {fm.start(): fm for fm in _FN.finditer(line)}
        for idx, ch in enumerate(line):
            if idx in fn_at:
                fm = fn_at[idx]
                mods = [v[0] for k, v, _ in stack if k == "mod"]
                impls = [v for k, v, _ in stack if k == "impl"]
                module = "::".join(([base_mod] if base_mod else []) + mods)
                it, tr, impl_generic, identity = (impls[-1] if impls else (None, None, False, ""))
                abs_end = line_starts[lineno - 1] + fm.end()
                params, ret, generic = _signature(clean, abs_end)
                prefix = clean[max(0, line_starts[lineno - 1] + fm.start() - 32) : line_starts[lineno - 1] + fm.start()]
                is_pub = bool(re.search(r"\bpub(\([^)]*\))?\s+(?:async\s+)?(?:const\s+)?(?:unsafe\s+)?$", prefix))
                fns.append(RustFn(
                    fm.group(1), module, it, tr, rel_path, lineno, params, ret, is_pub, crate,
                    generic=generic,
                    is_async=bool(re.search(r"\basync\s*$", prefix)),
                    is_unsafe=bool(re.search(r"\bunsafe\s*$", prefix)),
                    is_const=bool(re.search(r"\bconst\s*$", prefix)),
                    impl_generic=impl_generic,
                    doc=_doc_above(src_lines, lineno),
                    identity=identity,
                ))
            if ch == "{":
                if idx in headers:
                    stack.append((headers[idx][0], headers[idx][1], depth))
                depth += 1
            elif ch == "}":
                depth -= 1
                if stack and stack[-1][2] == depth:
                    stack.pop()
    return fns


def index_tree(root: str) -> list[RustFn]:
    """Index every Rust function of a Cargo workspace.

    Only workspace members are indexed: `horizon-mixins` refuses targets from excluded
    or third-party directories, so offering them as candidates would only produce a
    plan that fails. A plain directory (no workspace Cargo.toml) is indexed as-is.
    """
    out: list[RustFn] = []
    cache: dict[str, tuple[str, str] | None] = {}
    members = _workspace_members(root)
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("target", ".git", "node_modules")]
        for f in fn:
            if not f.endswith(".rs"):
                continue
            full = os.path.join(dp, f)
            info = _crate_root(full, cache)
            if members is not None:
                # A workspace: only members are valid targets for horizon-mixins.
                if info is None or os.path.normcase(info[0]) not in members:
                    continue
            if info is not None:
                crate_dir, crate = info
                src_dir = os.path.join(crate_dir, "src")
                rel = (os.path.relpath(full, src_dir) if full.startswith(src_dir + os.sep)
                       else os.path.relpath(full, crate_dir))
            else:
                crate, rel = "", os.path.relpath(full, root)
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    out.extend(index_source(fh.read(), rel, crate))
            except OSError:
                continue
    return out
