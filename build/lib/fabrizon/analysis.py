"""Feasibility analysis: which parts of a Fabric mod have a horizon-mixins counterpart.

The mapping table comes from horizon-mixins' own docs (docs/mixin-api.md and
docs/spongepowered-feature-gaps.md, Horizon Mixins 0.5/0.6). It answers "does a
*kind* exist?", not "can this *site* be hooked?" - the second question needs the
pinned Horizon source and comes in a later stage. So the statuses are:

  mappable  a counterpart exists and the common case is straightforward
  review    a counterpart exists but has site/type restrictions to verify
  blocked   no counterpart in horizon-mixins today
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .classfile import Annotation, ClassInfo
from .jar import JarInfo

MIXIN_PKG = "org/spongepowered/asm/mixin/"
EXTRAS_PKG = "com/llamalad7/mixinextras/"

# annotation simple name -> (horizon kind, status, note)
_SIMPLE: dict[str, tuple[str | None, str, str]] = {
    "Overwrite": ("OVERWRITE", "review", "Replaces the whole body and conflicts with every other hook on that function."),
    "ModifyArg": ("MODIFY_ARG", "review", "One argument, explicit index, same input/output type."),
    "ModifyArgs": ("MODIFY_ARGS", "review", "Typed tuple of all explicit call arguments."),
    "ModifyConstant": ("MODIFY_CONSTANT", "review", "Exact runtime literals only; compile-time expressions and implicit comparison constants are unsupported."),
    "ModifyVariable": ("MODIFY_VARIABLE", "review", "Plain locals/parameters; initializer or simple-assignment STORE and primitive scalar LOAD only."),
    "WrapOperation": ("WRAP_OPERATION", "review", "Typed FnOnce continuation; module-level free calls or borrowed parameter receivers."),
    "ModifyExpressionValue": ("MODIFY_EXPRESSION_VALUE", "review", "Exact syntax selector; runtime values only, not place expressions."),
    "ModifyReturnValue": ("RETURN", "review", "Closest counterpart is RETURN with result replacement; verify it fits."),
    "Accessor": ("bridge (GET/GET_MUT/SET)", "review", "Owned, non-generic structs only."),
    "Invoker": ("bridge (INVOKE)", "review", "Exact existing inherent/trait calls on owned, non-generic structs."),
    "Unique": ("[[state]] or [[module]]", "review", "Fields become namespaced per-instance state with explicit constructors; methods move into a support module."),
    "Redirect": (None, "blocked", "REDIRECT is not implemented in horizon-mixins."),
    "Shadow": (None, "blocked", "No declarative Shadow. Helpers can use ordinary same-crate privacy, so this may be rewritable by hand."),
    "Final": (None, "blocked", "No Java-style field finality control; Rust mutability rules apply."),
    "Mutable": (None, "blocked", "No Java-style field finality control; Rust mutability rules apply."),
    "Intrinsic": (None, "blocked", "No intrinsic-proxy mechanism."),
}

# annotations that are structural, handled elsewhere, or carry no behaviour
_IGNORED = {"Mixin", "Slice", "At", "Coerce", "Debug", "Group", "Dynamic", "Pseudo", "Inject", "Implements", "Interface"}


@dataclass
class Finding:
    mixin: str
    member: str
    annotation: str
    status: str
    horizon: str | None
    side: str
    targets: list[str]
    note: str
    selectors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class Report:
    mod_id: str
    version: str
    jar: str
    license: Any
    authors: list[str]
    entrypoints: dict[str, list[str]]
    intermediary_names: bool
    refmaps: list[str]
    asset_files: int
    data_files: int
    class_count: int
    mixin_class_count: int
    sides: dict[str, int]
    findings: list[Finding]
    fabric_api_refs: list[str]
    warnings: list[str]

    def counts(self) -> dict[str, int]:
        c = {"mappable": 0, "review": 0, "blocked": 0}
        for f in self.findings:
            c[f.status] += 1
        return c

    def to_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["findings"] = [f.to_dict() for f in self.findings]
        d["counts"] = self.counts()
        return d


def _internal(desc: str) -> str:
    return desc[1:-1] if desc.startswith("L") and desc.endswith(";") else desc.replace(".", "/")


def _mixin_targets(ci: ClassInfo) -> tuple[list[str], int | None]:
    for a in ci.annotations:
        if a.name == "Mixin" and a.internal_name.startswith(MIXIN_PKG):
            targets = [_internal(v) for v in a.values.get("value", []) if isinstance(v, str)]
            targets += [t.replace(".", "/") for t in a.values.get("targets", []) if isinstance(t, str)]
            return targets, a.values.get("priority")
    return [], None


def _as_list(v: Any) -> list[Any]:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _inject(a: Annotation, base: dict[str, Any]) -> list[Finding]:
    selectors = [s for s in _as_list(a.values.get("method")) if isinstance(s, str)]
    cancellable = bool(a.values.get("cancellable", False))
    extra = []
    if len(selectors) > 1:
        extra.append("multiple target methods: emit one injection per target")
    if any("*" in s for s in selectors):
        extra.append("wildcard target needs explicit expansion")
    if a.values.get("slice"):
        extra.append("has @Slice: horizon-mixins slices only bound by calls in one lexical block")
    if a.values.get("locals"):
        extra.append("captures locals: map to $local selectors")
    ats = [x for x in _as_list(a.values.get("at")) if isinstance(x, Annotation)]
    if not ats:
        return [Finding(**base, annotation="Inject", status="blocked", horizon=None, selectors=selectors,
                        note="no @At found")]
    out = []
    for at in ats:
        point = str(at.values.get("value", ""))
        shift = str(at.values.get("shift", "NONE"))
        ordinal = at.values.get("ordinal")
        notes = list(extra)
        if cancellable:
            notes.append("cancellable = true")
        status, kind = "review", None
        if point == "HEAD":
            status, kind = "mappable", "HEAD"
        elif point == "RETURN":
            status, kind = "mappable", "RETURN"
            notes.append("RETURN covers all exits; selecting an individual return is unsupported")
            if isinstance(ordinal, int) and ordinal >= 0:
                status = "blocked"
                kind = None
                notes.append("@At ordinal on RETURN selects one return: unsupported")
        elif point == "TAIL":
            status = "blocked"
            notes.append("TAIL is missing; RETURN is not an alias for it")
        elif point == "INVOKE":
            kind = "AFTER_CALL" if shift == "AFTER" else "BEFORE_CALL"
            notes.append("only whole statements, plain let initializers and block/function tails are hookable; needs an exact syntax selector, ordinal and exact require count")
        elif point == "INVOKE_ASSIGN":
            kind = "AFTER_ASSIGN"
            notes.append("captures the stored result after the assignment")
        elif point in ("FIELD", "NEW", "JUMP"):
            status = "blocked"
            notes.append(f"{point} injection sites are not implemented")
        elif point == "CONSTANT":
            status, kind = "review", "MODIFY_CONSTANT"
            notes.append("exact runtime literals only")
        else:
            status = "blocked"
            notes.append(f"injection point {point or '<custom>'} has no counterpart")
        if shift == "BY":
            status = "blocked"
            kind = None
            notes.append("relative instruction offsets (shift = BY) are not implemented")
        out.append(Finding(**base, annotation=f"Inject@{point or '?'}", status=status, horizon=kind,
                           selectors=selectors, note="; ".join(notes)))
    return out


def analyze(jar: JarInfo) -> Report:
    m = jar.manifest
    findings: list[Finding] = []
    sides: dict[str, int] = {"common": 0, "client": 0, "server": 0}

    for mc in jar.mixin_classes:
        ci = mc.info
        sides[mc.side] += 1
        targets, _prio = _mixin_targets(ci)
        base = dict(mixin=ci.name, member="", side=mc.side, targets=targets)

        if ci.is_interface:
            findings.append(Finding(**{**base, "member": "(class)"}, annotation="interface mixin", status="blocked",
                                    horizon=None, note="interface and soft-implements mixins are not implemented"))
        if any(a.name == "Implements" for a in ci.annotations):
            findings.append(Finding(**{**base, "member": "(class)"}, annotation="Implements", status="blocked",
                                    horizon=None, note="soft-implements mixins are not implemented"))

        for member in list(ci.methods) + list(ci.fields):
            mbase = {**base, "member": member.name}
            for a in member.annotations:
                pkg = a.internal_name
                if not (pkg.startswith(MIXIN_PKG) or pkg.startswith(EXTRAS_PKG)):
                    continue
                if a.name == "Inject":
                    findings.extend(_inject(a, mbase))
                elif a.name in _SIMPLE:
                    kind, status, note = _SIMPLE[a.name]
                    sel = [s for s in _as_list(a.values.get("method")) if isinstance(s, str)]
                    findings.append(Finding(**mbase, annotation=a.name, status=status, horizon=kind,
                                            selectors=sel, note=note))
                elif a.name not in _IGNORED:
                    findings.append(Finding(**mbase, annotation=a.name, status="blocked", horizon=None,
                                            note="no documented counterpart in horizon-mixins"))

    refmaps = sorted({c.refmap for c in jar.configs if c.refmap})
    return Report(
        mod_id=str(m.get("id", "?")),
        version=str(m.get("version", "?")),
        jar=jar.path,
        license=m.get("license"),
        authors=[a if isinstance(a, str) else str(a.get("name", a)) for a in m.get("authors", []) or []],
        entrypoints={k: [v if isinstance(v, str) else str(v.get("value", v)) for v in vs]
                     for k, vs in (m.get("entrypoints") or {}).items() if isinstance(vs, list)},
        intermediary_names=jar.intermediary_names,
        refmaps=refmaps,
        asset_files=jar.asset_files,
        data_files=jar.data_files,
        class_count=jar.class_count,
        mixin_class_count=len(jar.mixin_classes),
        sides=sides,
        findings=findings,
        fabric_api_refs=jar.fabric_api_refs,
        warnings=jar.warnings,
    )
