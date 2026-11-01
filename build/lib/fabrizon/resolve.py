"""Candidate matcher: Fabric mixin targets -> likely Horizon Rust functions.

Stage 2, piece 3. For each finding it maps the target class and method selector through the
mappings (if given), then ranks Rust functions whose impl type and fn name look alike.
Output is a ranked candidate list, never a verdict: Horizon's names are not guaranteed to
follow Java's, so a human (or stage 3 with the pinned source) must confirm each pick.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .analysis import Report
from .mappings import Mappings
from .rustindex import RustFn


def snake(name: str) -> str:
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


_INTERMEDIARY = re.compile(r"^(class|method|field)_\d+$")


@dataclass
class Selector:
    owner: str | None
    name: str
    desc: str | None
    raw: str


def parse_selector(sel: str) -> Selector:
    """Parse a Mixin method selector: `name`, `name(desc)ret`, `Lowner;name(desc)ret`."""
    raw = sel
    owner = None
    if sel.startswith("L") and ";" in sel.split("(")[0]:
        owner_s, sel = sel.split(";", 1)
        owner = owner_s[1:]
    desc = None
    if "(" in sel:
        sel, d = sel.split("(", 1)
        desc = "(" + d
    return Selector(owner, sel, desc, raw)


@dataclass
class Candidate:
    path: str
    file: str
    line: int
    score: int
    why: list[str]
    crate: str = ""
    ret: str | None = None
    params: list[dict[str, str]] = field(default_factory=list)
    target: str = ""  # exact horizon-mixins ID path: module::identity::fn


@dataclass
class Resolution:
    mixin: str
    annotation: str
    java_target: str
    java_method: str
    readable_target: str | None
    readable_method: str | None
    status: str  # resolved | ambiguous | unresolved | needs-mappings
    kind: str | None = None      # horizon-mixins kind from the analysis (HEAD, RETURN, ...)
    member: str = ""             # Java handler method name in the mixin class
    side: str = "common"
    candidates: list[Candidate] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["candidates"] = [c.__dict__ for c in self.candidates]
        return d


def _simple(cls: str) -> str:
    return cls.split("/")[-1].split("$")[-1]


_PRIM = {"I": {"i32", "u32", "i64", "usize"}, "J": {"i64", "u64", "usize"}, "F": {"f32"},
         "D": {"f64"}, "Z": {"bool"}, "B": {"i8", "u8"}, "C": {"char", "u16"}, "S": {"i16", "u16"}}
_PRIM_DESC = set("IJFDZBCS")


def desc_params(desc: str | None) -> list[str]:
    """Split a JVM method descriptor into its parameter type descriptors."""
    if not desc or not desc.startswith("("):
        return []
    out, i, n = [], 1, len(desc)
    while i < n and desc[i] != ")":
        j = i
        while j < n and desc[j] == "[":
            j += 1
        if j < n and desc[j] == "L":
            k = desc.find(";", j)
            k = n if k < 0 else k + 1
            out.append(desc[i:k])
            i = k
        else:
            out.append(desc[i : j + 1])
            i = j + 1
    return out


def _affinity(java_desc: str, rust_ty: str) -> bool:
    """Whether a Rust parameter type plausibly corresponds to a JVM type descriptor."""
    base = rust_ty.strip()
    for prefix in ("&mut ", "&", "mut "):
        if base.startswith(prefix):
            base = base[len(prefix) :]
    base = base.strip()
    if java_desc.startswith("["):
        return base.startswith(("Vec<", "&[", "[", "Option<Vec<"))
    if java_desc in _PRIM_DESC:
        return base in _PRIM[java_desc] or (java_desc == "Z" and "bool" in base)
    if java_desc.startswith("L"):
        internal = java_desc[1:-1]
        name = internal.split("/")[-1].split("$")[-1]
        if name in ("Object", "String"):
            return base in ("String", "&str", "str", "Option<&str>") or "String" in base or "str" in base
        return base.split("<")[0].split("::")[-1] == name or name in base
    return False


def rank(fns: list[RustFn], cls: str | None, method: str | None, limit: int = 5,
         desc: str | None = None) -> list[Candidate]:
    want_fn = snake(method) if method else None
    want_ty = _simple(cls) if cls else None
    jparams = desc_params(desc)
    out: list[Candidate] = []
    for f in fns:
        if not f.hookable:
            continue  # horizon-mixins rejects generic/const/unsafe/async targets
        score, why = 0, []
        if want_fn:
            if f.name == want_fn:
                score += 50; why.append(f"fn name matches `{want_fn}`")
            elif want_fn in f.name or f.name in want_fn:
                score += 15; why.append(f"fn name similar to `{want_fn}`")
        if want_ty and f.impl_type:
            if f.impl_type == want_ty:
                score += 40; why.append(f"impl type matches `{want_ty}`")
            elif snake(f.impl_type) == snake(want_ty):
                score += 35; why.append(f"impl type matches `{want_ty}` ignoring case style")
            elif snake(want_ty) in snake(f.impl_type):
                score += 10; why.append(f"impl type resembles `{want_ty}`")
        if want_ty and not f.impl_type and snake(want_ty) in f.module.split("::"):
            score += 20; why.append(f"free fn in module `{snake(want_ty)}`")
        if f.doc:
            low = f.doc.lower()
            if want_fn and (want_fn in low or (method and method.lower() in low)):
                score += 45; why.append(f"doc comment names `{method}`")
            if want_ty and snake(want_ty) in low:
                score += 15; why.append(f"doc comment names `{want_ty}`")
        if jparams:
            if f.arity == len(jparams):
                score += 12; why.append(f"{f.arity} parameter(s) like the Java method")
            elif abs(f.arity - len(jparams)) == 1:
                score += 4
            hits = sum(
                1
                for jt in jparams
                if any(_affinity(jt, p.ty) for p in f.params if not p.is_self)
            )
            if hits:
                score += min(hits * 4, 16)
                why.append(f"{hits}/{len(jparams)} parameter type(s) look alike")
        if want_fn and want_ty and score < 50:
            continue
        if score and (not want_fn or any("fn name" in w for w in why)):
            out.append(Candidate(f.path, f.file, f.line, score, why, f.crate, f.ret,
                                 [{"name": p.name, "ty": p.ty} for p in f.params],
                                 f.target_path))
    out.sort(key=lambda c: (-c.score, c.path))
    return out[:limit]


def resolve(report: Report, fns: list[RustFn], maps: Mappings | None = None,
            to_ns: str = "named") -> list[Resolution]:
    results: list[Resolution] = []
    for f in report.findings:
        if f.status == "blocked" and not f.selectors:
            continue
        targets = f.targets or [""]
        sels = [parse_selector(s) for s in f.selectors] or [Selector(None, "", None, "")]
        for t in targets:
            for s in sels:
                notes: list[str] = []
                cls, meth = t or None, s.name or None
                intermediary = bool((t and _INTERMEDIARY.match(t.split("/")[-1])) or (meth and _INTERMEDIARY.match(meth)))
                if maps is not None:
                    if t:
                        mapped = maps.map_class(t, to_ns)
                        if mapped:
                            cls = mapped
                        elif _INTERMEDIARY.match(t.split("/")[-1]):
                            notes.append(f"class {t} not found in mappings")
                    if meth:
                        names = maps.map_methods(meth, to_ns, owner=t or None)
                        if names:
                            meth = names[0]
                            if len(names) > 1:
                                notes.append(f"method maps to several names: {', '.join(names)}")
                        elif _INTERMEDIARY.match(meth):
                            notes.append(f"method {meth} not found in mappings")
                elif intermediary:
                    results.append(Resolution(f.mixin, f.annotation, t, s.name, None, None, "needs-mappings", f.horizon, f.member, f.side,
                                              notes=["intermediary names: pass --mappings (Tiny v1/v2)"]))
                    continue
                cands = rank(fns, cls, meth, desc=s.desc) if fns else []
                if not fns:
                    notes.append("no Horizon source indexed: pass --horizon")
                still_obf = bool((cls and _INTERMEDIARY.match(cls.split("/")[-1])) or (meth and _INTERMEDIARY.match(meth)))
                if still_obf:
                    status = "unresolved"
                elif not cands:
                    status = "unresolved"
                elif len(cands) == 1 or cands[0].score - cands[1].score >= 30:
                    status = "resolved"
                else:
                    status = "ambiguous"
                results.append(Resolution(f.mixin, f.annotation, t, s.name, cls, meth, status, f.horizon, f.member, f.side, cands, notes))
    return results


def render_resolutions(rs: list[Resolution]) -> str:
    lines = ["Fabrizon stage 2: name resolution (candidates, not verdicts)", ""]
    for r in rs:
        lines.append(f"[{r.status}] {r.mixin} @{r.annotation}")
        lines.append(f"    java: {r.java_target}#{r.java_method}")
        if r.readable_target or r.readable_method:
            lines.append(f"    named: {r.readable_target}#{r.readable_method}")
        for c in r.candidates:
            lines.append(f"    -> {c.path}  ({c.file}:{c.line}, score {c.score}; {'; '.join(c.why)})")
        for n in r.notes:
            lines.append(f"    note: {n}")
    tally: dict[str, int] = {}
    for r in rs:
        tally[r.status] = tally.get(r.status, 0) + 1
    lines += ["", "summary: " + (", ".join(f"{k} {v}" for k, v in sorted(tally.items())) or "nothing to resolve")]
    return "\n".join(lines) + "\n"
