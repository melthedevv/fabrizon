"""Render a Report as text or JSON."""

from __future__ import annotations

import json

from .analysis import Report

_ORDER = ("blocked", "review", "mappable")
_TAG = {"blocked": "BLOCKED ", "review": "REVIEW  ", "mappable": "MAPPABLE"}


def render_json(r: Report) -> str:
    return json.dumps(r.to_dict(), indent=2, sort_keys=True)


def render_text(r: Report) -> str:
    c = r.counts()
    total = sum(c.values())
    lines = [f"Fabrizon feasibility report: {r.mod_id} {r.version}", f"  jar: {r.jar}"]
    if r.license:
        lines.append(f"  license: {r.license}  (keep it and credit the author in any translation)")
    if r.authors:
        lines.append(f"  authors: {', '.join(r.authors)}")

    lines += ["", "Content"]
    lines.append(f"  {r.asset_files} asset file(s), {r.data_files} data file(s): these go to a content mod / data+resource pack path")

    lines += ["", "Code"]
    lines.append(f"  {r.class_count} class(es), {r.mixin_class_count} mixin class(es) "
                 f"(common {r.sides['common']}, client {r.sides['client']}, server {r.sides['server']})")
    for kind, eps in r.entrypoints.items():
        lines.append(f"  entrypoint {kind}: {', '.join(eps)}")
    if r.intermediary_names:
        lines.append("  names: intermediary names detected (class_1234/method_5678): a mappings step is required "
                     "before targets can be resolved to Horizon's Rust paths")
    elif r.refmaps:
        lines.append(f"  names: refmap present ({', '.join(r.refmaps)}): target names may need remapping")
    else:
        lines.append("  names: no intermediary names detected")

    lines += ["", f"Injection points: {total} found  "
              f"({c['mappable']} mappable, {c['review']} need review, {c['blocked']} blocked)"]
    lines.append("  'mappable'/'review' mean a horizon-mixins kind exists. Whether the exact site can be hooked")
    lines.append("  needs the pinned Horizon source and is not checked yet.")
    for status in _ORDER:
        group = [f for f in r.findings if f.status == status]
        if not group:
            continue
        lines.append("")
        for f in group:
            arrow = f" -> {f.horizon}" if f.horizon else ""
            tgt = f" [{', '.join(f.targets)}]" if f.targets else ""
            lines.append(f"  {_TAG[status]} {f.mixin.rsplit('/', 1)[-1]}#{f.member} @{f.annotation}{arrow} ({f.side}){tgt}")
            if f.selectors:
                lines.append(f"           target method: {', '.join(f.selectors)}")
            if f.note:
                lines.append(f"           {f.note}")

    if r.fabric_api_refs:
        lines += ["", "Fabric API usage (not mixins: needs an event -> injection-site table)"]
        lines += [f"  {x.replace('/', '.')}" for x in r.fabric_api_refs]
    if r.warnings:
        lines += ["", "Warnings"] + [f"  {w}" for w in r.warnings]
    return "\n".join(lines) + "\n"
