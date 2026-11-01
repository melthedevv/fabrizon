"""fabrizon command line."""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .analysis import analyze
from .jar import NotAFabricMod, read_jar
from .report import render_json, render_text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="fabrizon",
        description="Translate Fabric mods for Horizon. Unofficial. Made by melthedev (https://ko-fi.com/melthedev).",
    )
    p.add_argument("--version", action="version", version=f"fabrizon {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="feasibility report for a Fabric mod jar")
    a.add_argument("jar")
    a.add_argument("--json", action="store_true", help="machine-readable output")

    r = sub.add_parser("resolve", help="stage 2: map a mod's mixin targets to candidate Horizon Rust functions")
    r.add_argument("jar")
    r.add_argument("--mappings", help="Tiny v1/v2 mappings file (.tiny or .gz), e.g. intermediary or Yarn")
    r.add_argument("--to", default="named", help="namespace to map to (default: named)")
    r.add_argument("--horizon", help="path to a Horizon source checkout to index")
    r.add_argument("--json", action="store_true", help="machine-readable output")

    ge = sub.add_parser("generate", help="stage 3+4: write a horizon-mixins bundle with translated helpers")
    ge.add_argument("jar")
    ge.add_argument("--mappings", help="Tiny v1/v2 mappings file (.tiny or .gz)")
    ge.add_argument("--to", default="named", help="namespace to map to (default: named)")
    ge.add_argument("--horizon", required=True, help="path to a Horizon source checkout")
    ge.add_argument("--crate", default="horizon_core",
                    help="fallback Cargo target name when the checkout has no Cargo.toml (default: horizon_core)")
    ge.add_argument("--revision", help="exact 40-char Horizon commit for [compatibility]")
    ge.add_argument("--out", required=True, help="output folder for the bundle")
    ge.add_argument("--hnmod", metavar="FILE", help="also package the bundle as a .hnmod")
    ge.add_argument("--game", help="Minecraft version for the .hnmod manifest (e.g. 26.3)")
    ge.add_argument("--compatibility", help="compatibility.json to take game/revisions/hooks from")
    ge.add_argument("--mixins-revision", help="exact 40-char horizon-mixins commit for the .hnmod")
    ge.add_argument("--hooks", type=int, help="NATIVE_HOOKS_API the mod needs (default: the checkout's)")
    # AI-assisted translation options
    ge.add_argument("--ai-api-key", help="NVIDIA API key for AI-assisted translation (or set FABRIZON_NVIDIA_API_KEY env)")
    ge.add_argument("--ai-base-url", default="https://integrate.api.nvidia.com/v1", help="OpenAI-compatible API base URL")
    ge.add_argument("--ai-model", default="nvidia/nemotron-3-ultra-550b-a55b", help="Model name for AI translation")
    ge.add_argument("--ai-config", help="JSON file with ai_api_key, base_url, model, temperature, max_tokens")

    pk = sub.add_parser("package", help="stage 5: package a bundle folder as a deterministic .hnmod")
    pk.add_argument("bundle", help="folder containing horizon-mixin.toml")
    pk.add_argument("--out", required=True, help="output .hnmod path")
    pk.add_argument("--compatibility", help="compatibility.json with game/revisions/hooks")
    pk.add_argument("--horizon", help="Horizon checkout, to read NATIVE_HOOKS_API when --hooks is absent")
    pk.add_argument("--game", help="Minecraft version (e.g. 26.3)")
    pk.add_argument("--horizon-revision", help="exact 40-char Horizon commit")
    pk.add_argument("--mixins-revision", help="exact 40-char horizon-mixins commit")
    pk.add_argument("--hooks", type=int, help="NATIVE_HOOKS_API the mod needs")
    pk.add_argument("--json", action="store_true", help="machine-readable output")

    g = sub.add_parser("gui", help="open the Fabrizon app in your browser")
    g.add_argument("--port", type=int, default=0, help="port (default: any free port)")
    g.add_argument("--no-browser", action="store_true", help="don't open a browser tab automatically")
    args = p.parse_args(argv)

    if args.cmd == "analyze":
        try:
            report = analyze(read_jar(args.jar))
        except NotAFabricMod as e:
            print(f"fabrizon: {e}", file=sys.stderr)
            return 2
        sys.stdout.write(render_json(report) + "\n" if args.json else render_text(report))
        return 0

    if args.cmd == "generate":
        from .generate import generate, write_bundle
        from .mappings import MappingError, load_tiny
        from .package import PackageError, build_compatibility, load_compatibility, package_bundle
        from .resolve import resolve
        from .rustindex import index_tree
        try:
            jar = read_jar(args.jar)
            report = analyze(jar)
            maps = load_tiny(args.mappings) if args.mappings else None
            rs = resolve(report, index_tree(args.horizon), maps, args.to)

            # Build AI config if provided
            ai_config = None
            if args.ai_config:
                try:
                    from .ai_translate import AIConfig
                    ai_config = AIConfig.from_file(args.ai_config)
                except Exception as e:
                    print(f"fabrizon: failed to load AI config: {e}", file=sys.stderr)
                    return 2
            elif args.ai_api_key or os.environ.get("FABRIZON_NVIDIA_API_KEY") or os.environ.get("NVIDIA_API_KEY"):
                try:
                    from .ai_translate import AIConfig
                    ai_config = AIConfig(
                        api_key=args.ai_api_key or os.environ.get("FABRIZON_NVIDIA_API_KEY") or os.environ.get("NVIDIA_API_KEY") or "",
                        base_url=args.ai_base_url,
                        model=args.ai_model,
                    )
                except Exception as e:
                    print(f"fabrizon: failed to create AI config: {e}", file=sys.stderr)
                    return 2

            b = generate(report, rs, args.crate, args.revision, jar, ai_config)
            paths = write_bundle(b, args.out)
            packed = None
            if args.hnmod:
                base = load_compatibility(args.compatibility) if args.compatibility else {}
                compat = build_compatibility(
                    args.horizon, game=args.game, horizon_revision=args.revision,
                    mixins_revision=args.mixins_revision, hooks=args.hooks, base=base,
                )
                packed = package_bundle(args.out, args.hnmod, compat)
        except (NotAFabricMod, MappingError, PackageError, ValueError, OSError) as e:
            print(f"fabrizon: {e}", file=sys.stderr)
            return 2
        print(f"wrote {len(paths)} files to {args.out}; {len(b.emitted)} injection(s), "
              f"{len(b.todo)} item(s) in TODO.md")
        if packed:
            print(f"packaged {packed.path} ({packed.size} bytes, sha256 {packed.sha256})")
        return 0

    if args.cmd == "package":
        from .package import PackageError, build_compatibility, load_compatibility, package_bundle
        try:
            base = load_compatibility(args.compatibility) if args.compatibility else {}
            compat = build_compatibility(
                args.horizon, game=args.game, horizon_revision=args.horizon_revision,
                mixins_revision=args.mixins_revision, hooks=args.hooks, base=base,
            )
            packed = package_bundle(args.bundle, args.out, compat)
        except (PackageError, OSError) as e:
            print(f"fabrizon: {e}", file=sys.stderr)
            return 2
        if args.json:
            sys.stdout.write(json.dumps(packed.to_dict(), indent=2) + "\n")
        else:
            print(f"packaged {packed.path} ({packed.size} bytes, sha256 {packed.sha256})")
        return 0

    if args.cmd == "gui":
        from .gui import serve
        return serve(args.port, not args.no_browser)

    if args.cmd == "resolve":
        from .mappings import MappingError, load_tiny
        from .resolve import render_resolutions, resolve
        from .rustindex import index_tree
        try:
            report = analyze(read_jar(args.jar))
            maps = load_tiny(args.mappings) if args.mappings else None
            fns = index_tree(args.horizon) if args.horizon else []
            rs = resolve(report, fns, maps, args.to)
        except (NotAFabricMod, MappingError, OSError) as e:
            print(f"fabrizon: {e}", file=sys.stderr)
            return 2
        if args.json:
            sys.stdout.write(json.dumps([r.to_dict() for r in rs], indent=2) + "\n")
        else:
            sys.stdout.write(render_resolutions(rs))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
