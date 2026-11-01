"""Read a Fabric mod jar: manifest, mixin configs, mixin classes, assets and data."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from typing import Any

from .classfile import ClassFormatError, ClassInfo, parse_class

_INTERMEDIARY = re.compile(r"\b(?:class|method|field)_\d{2,}\b")


class NotAFabricMod(ValueError):
    pass


@dataclass
class MixinConfig:
    name: str
    package: str
    refmap: str | None
    environment: str  # "*", "client" or "server"
    common: list[str]
    client: list[str]
    server: list[str]


@dataclass
class MixinClass:
    path: str  # path inside the jar
    side: str  # "common", "client" or "server"
    config: str
    info: ClassInfo


@dataclass
class JarInfo:
    path: str
    manifest: dict[str, Any]
    configs: list[MixinConfig] = field(default_factory=list)
    mixin_classes: list[MixinClass] = field(default_factory=list)
    class_count: int = 0
    asset_files: int = 0
    data_files: int = 0
    nested_jars: int = 0
    fabric_api_refs: list[str] = field(default_factory=list)
    intermediary_names: bool = False
    warnings: list[str] = field(default_factory=list)


def _manifest_configs(manifest: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for item in manifest.get("mixins", []) or []:
        if isinstance(item, str):
            out.append((item, "*"))
        elif isinstance(item, dict) and "config" in item:
            out.append((item["config"], item.get("environment", "*")))
    return out


def read_jar(path: str) -> JarInfo:
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError, IsADirectoryError) as e:
        raise NotAFabricMod(f"cannot open {path}: {e}") from e

    with zf:
        names = zf.namelist()
        if "fabric.mod.json" not in names:
            raise NotAFabricMod("no fabric.mod.json at the root of the jar (not a Fabric mod?)")
        try:
            manifest = json.loads(zf.read("fabric.mod.json").decode("utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise NotAFabricMod(f"fabric.mod.json is not valid JSON: {e}") from e

        info = JarInfo(path=path, manifest=manifest)
        info.asset_files = sum(1 for n in names if n.startswith("assets/") and not n.endswith("/"))
        info.data_files = sum(1 for n in names if n.startswith("data/") and not n.endswith("/"))
        info.nested_jars = sum(1 for n in names if n.startswith("META-INF/jars/") and n.endswith(".jar"))
        if info.nested_jars:
            info.warnings.append(
                f"{info.nested_jars} nested jar(s) in META-INF/jars were not analyzed"
            )

        # mixin configs -> classes and sides
        class_side: dict[str, tuple[str, str]] = {}
        for cfg_name, env in _manifest_configs(manifest):
            if cfg_name not in names:
                info.warnings.append(f"mixin config {cfg_name} is listed but missing from the jar")
                continue
            try:
                raw = json.loads(zf.read(cfg_name).decode("utf-8-sig"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                info.warnings.append(f"mixin config {cfg_name} is not valid JSON: {e}")
                continue
            cfg = MixinConfig(
                name=cfg_name,
                package=raw.get("package", ""),
                refmap=raw.get("refmap"),
                environment=env,
                common=list(raw.get("mixins", [])),
                client=list(raw.get("client", [])),
                server=list(raw.get("server", [])),
            )
            info.configs.append(cfg)
            for group, side in ((cfg.common, "common"), (cfg.client, "client"), (cfg.server, "server")):
                for cls_name in group:
                    if env in ("client", "server"):
                        side = env
                    rel = (cfg.package.replace(".", "/") + "/" if cfg.package else "") + cls_name.replace(".", "/")
                    class_side[rel + ".class"] = (side, cfg_name)

        api_refs: set[str] = set()
        for n in names:
            if not n.endswith(".class") or n.startswith("META-INF/"):
                continue
            info.class_count += 1
            try:
                ci = parse_class(zf.read(n))
            except ClassFormatError as e:
                info.warnings.append(f"could not read {n}: {e}")
                continue
            api_refs.update(r for r in ci.class_refs if r.startswith("net/fabricmc/fabric/api/"))
            if n in class_side:
                side, cfg_name = class_side[n]
                info.mixin_classes.append(MixinClass(n, side, cfg_name, ci))
                if any(_INTERMEDIARY.search(s) for s in ci.utf8):
                    info.intermediary_names = True

        for n in class_side:
            if n not in names:
                info.warnings.append(f"mixin class {n} is listed in a config but missing from the jar")
        info.fabric_api_refs = sorted(api_refs)
    return info
