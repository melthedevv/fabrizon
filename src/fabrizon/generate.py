"""Stage 3: emit a horizon-mixins bundle (horizon-mixin.toml + helper .rs files).

Format source: horizon-mixins docs/mixin-api.md, advanced-injections.md and
scopes-and-bridges.md (0.6.0, plan schema 6).

Live injections are limited to the kinds whose contract is fully specified
without the target's AST: HEAD (including cancellable HEAD) and RETURN. Every
other kind needs exact selectors, counts, ordinals or typed contracts that a jar
cannot supply, so those are listed in TODO.md for a human instead of being
guessed into TOML that would fail `horizon-mixins plan`.

Helper bodies come from `translate.py`: whatever is mechanically safe is Rust,
the rest is a comment plus a BRIEF.md entry. Nothing here is verified until you
run `horizon-mixins plan` / `check` against the pinned Horizon source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .analysis import Report
from .resolve import Resolution
from .translate import AI_NOTE, Helper, build_helper, render_brief
try:
    from .ai_translate import AIConfig
except Exception:
    AIConfig = None  # type: ignore

KIND_RESTRICTION = {
    "HEAD": None,
    "RETURN": None,
    "BEFORE_CALL": "needs an exact syntax selector, `require` count and `ordinal` from the target's AST",
    "AFTER_CALL": "needs an exact syntax selector, `require` count and `ordinal` from the target's AST",
    "AFTER_ASSIGN": "needs an exact selector and the assignment site's AST",
    "MODIFY_ARG": "needs the call selector and the argument index in the target's AST",
    "MODIFY_ARGS": "needs the call selector and a typed argument tuple from the target's AST",
    "MODIFY_CONSTANT": "needs the literal's exact spelling and ordinal in the target's AST",
    "MODIFY_VARIABLE": "needs a `$local` selector and the local's type from the target's AST",
    "MODIFY_EXPRESSION_VALUE": "needs an exact syntax selector in the target's AST",
    "WRAP_OPERATION": "needs the call selector and a typed `impl FnOnce` continuation",
    "OVERWRITE": "replaces the whole body, so the entire body must be translated first",
}


def _slug(s: str) -> str:
    """Registry rule: lowercase letters, digits and `_`."""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or "mod"


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def target_id(crate: str, path: str) -> str:
    """Horizon fn path (module::Type::fn) -> horizon-mixins target ID (crate::module::Type::fn)."""
    return f"{crate.replace('-', '_')}::{path}"


def candidate_target(cand, crate: str) -> str:
    """The exact ID horizon-mixins will resolve, including the impl identity.

    horizon-mixins builds `{crate}::{module}::{identity}::{fn}`, where the identity is
    the self type with lifetimes normalised to `'_` (and `<Type as Trait>` for trait
    impls). Using the friendly `Type` spelling here would be rejected by `plan`.
    """
    return target_id(cand.crate or crate, cand.target or cand.path)


@dataclass
class Bundle:
    files: dict[str, str] = field(default_factory=dict)
    emitted: list[str] = field(default_factory=list)
    todo: list[str] = field(default_factory=list)
    helpers: list[Helper] = field(default_factory=list)


def generate(report: Report, resolutions: list[Resolution], crate: str,
             horizon_revision: str | None = None, jar=None,
             ai_config: "AIConfig | None" = None) -> Bundle:
    b = Bundle()
    mod_id = _slug(report.mod_id)
    toml = ["[mod]", f"id = {_q(mod_id)}",
            f"version = {_q(report.version if report.version != '?' else '0.1.0')}", "priority = 100", ""]
    if horizon_revision:
        if not re.fullmatch(r"[0-9a-f]{40}", horizon_revision):
            raise ValueError("horizon_revision must be an exact 40-character commit hash")
        toml += ["[compatibility]", f"horizon_revision = {_q(horizon_revision)}", ""]
    used: set[str] = set()
    for r in resolutions:
        label = f"{r.mixin.split('/')[-1]}#{r.member} ({r.annotation}) -> {r.java_target.split('/')[-1]}#{r.java_method}"
        if r.status != "resolved" or not r.candidates:
            b.todo.append(f"- [{r.status}] {label}: no confirmed Horizon target; resolve by hand.")
            continue
        cand = r.candidates[0]
        tid = candidate_target(cand, crate)
        restriction = KIND_RESTRICTION.get(r.kind or "", "no documented counterpart")
        if restriction is not None:
            b.todo.append(f"- [{r.kind or 'no kind'}] {label}: needs a hand-written injection "
                          f"(target `{tid}`): {restriction}.")
            continue
        helper = build_helper(r, jar, crate, ai_config)
        if helper is None:
            b.todo.append(f"- [{r.kind}] {label}: could not read the handler body; write it by hand.")
            continue
        base = helper.fn_name
        iid, n = base.replace("_", "-"), 2
        while iid in used:
            iid, n = f"{base.replace('_', '-')}-{n}", n + 1
        used.add(iid)
        helper.fn_name = helper.fn_name
        helper.filename = base + ".rs"
        bindings = ", ".join(bd.toml() for bd in helper.bindings)
        toml += ["[[injection]]", f"id = {_q(iid)}", f"target = {_q(tid)}", f"kind = {_q(r.kind)}"]
        if r.kind == "HEAD" and helper.cancellable:
            toml.append("cancellable = true")
        toml += [f"helper = {_q(helper.filename)}", f"bindings = [{bindings}]", ""]
        b.files[helper.filename] = helper.source
        b.helpers.append(helper)
        b.emitted.append(tid)
        if r.side != "common":
            b.todo.append(f"- [{r.side}-only] {label}: Fabric runs this on the {r.side} only; check the Horizon target's thread/side.")
        if not helper.complete:
            b.todo.append(f"- [translate] {label}: `{helper.filename}` still has TODO lines "
                          f"({'; '.join(helper.notes[:3]) or 'untranslated statements'}); see BRIEF.md.")
    if b.emitted:
        b.files["horizon-mixin.toml"] = "\n".join(toml).rstrip() + "\n"
    lic = report.license if isinstance(report.license, str) else (", ".join(map(str, report.license)) if report.license else "not declared")
    authors = ", ".join(report.authors) or "unknown"
    b.files["NOTICE.md"] = (f"# Notice\n\nThis bundle was generated by Fabrizon from the Fabric mod `{report.mod_id}` {report.version}.\n\n"
                            f"- Original authors: {authors}\n- Original license: {lic}\n\n"
                            "A translation is a derivative work. Keep this notice, keep the original license and credit, and only publish it if that license allows derivatives.\n"
                            "Generated by Fabrizon (unofficial, not affiliated with Horizon, Mojang or Microsoft). Made by melthedev - https://ko-fi.com/melthedev\n")
    b.files["TODO.md"] = ("# Needs a human\n\nVerify with `horizon-mixins plan` then `check` on the pinned Horizon source before trusting anything here.\n\n"
                          + ("\n".join(b.todo) if b.todo else "Nothing flagged, which still does not mean it compiles.") + "\n")
    b.files["BRIEF.md"] = render_brief(b.helpers, crate, report.mod_id)
    return b


def write_bundle(b: Bundle, out_dir: str) -> list[str]:
    import os
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name, text in b.files.items():
        p = os.path.join(out_dir, name)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        paths.append(p)
    return paths
