<img src="assets/icon.svg" width="64" height="64" alt="Fabrizon logo">

<div align="center">

# Fabrizon

**Translate Fabric mods for [Horizon](https://github.com/horizon-rust/horizon).**

Drop in a Fabric mod `.jar`, get a feasibility report, candidate Horizon targets, and a ready-to-check `horizon-mixins` bundle.

Made by **melthedev** 

[![Support me on ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/J7L822JO4Y)

</div>

> **Unofficial.** Fabrizon is a community project. It is not made by, affiliated with, or endorsed by the Horizon project, Mojang or Microsoft. It contains no Minecraft code or assets.

---

## Status

| Stage | Command | What it does |
|-------|---------|--------------|
| 1 | `analyze` | Read a jar, classify every mixin injection point (mappable / review / blocked) |
| 2 | `resolve` | Map Fabric targets through Tiny mappings, index a Horizon checkout, rank candidate Rust functions |
| 3 | `generate` | Write a horizon-mixins bundle. Live injections for HEAD (incl. cancellable) and RETURN; the rest listed in `TODO.md` |
| 4 | `generate` (with `--out`) | Decompile mixin handler bytecode; mechanically safe parts translated to Rust; rest commented + `BRIEF.md` |
| 5 | `package` | Package the bundle folder as a deterministic `.hnmod` zip (sorted, fixed timestamp, 512 files / 64 MiB) |

`python -m pytest -q` runs 31 tests (standard library only). Real-data verification (2026-11-01):

- Horizon `ba6344a59cb9e755b730dcf02285fc0d33b97d3c`, horizon-mixins `d9c83d7096b7ea5b83678da2efdfd6161f74997e` (0.6.0, schema 6)
- Yarn `1.21+build.9` (v2 tiny), Vein Mining jar, Zoomify jar, voicechat jar
- `horizon-mixins plan` OK on generated bundles; `.hnmod` produced and read back

Limitations apply; see the `TODO.md` / `BRIEF.md` a bundle produces.

---

## Quick start

**Requirements:** Python 3.10 or newer. No other dependencies.

```bash
unzip fabrizon.zip && cd fabrizon

# GUI (easiest): double-click fabrizon_gui.pyw, or:
```

Because the package lives in `src/`, either install it or point Python at it:

```bash
pip install .                   # gives you the `fabrizon` command
fabrizon gui

# or without installing:
PYTHONPATH=src python -m fabrizon gui          # Linux / macOS
set PYTHONPATH=src && python -m fabrizon gui   # Windows cmd
```

The double-click launcher `fabrizon_gui.pyw` sets the path for you.

**Typical workflow**

1. Get a Fabric mod jar (ideally a simple, server-side one to start).
2. Run `analyze` (or drop it in the GUI) to see what is translatable.
3. If the report says *intermediary names*, get a Tiny mappings file (Fabric intermediary, or Yarn) and run `resolve` with `--horizon` pointing at your Horizon source checkout.
4. Run `generate` to write the bundle.
5. Run the real tool on the bundle: `horizon-mixins plan`, then `check` (see [Sources](#sources)). Fabrizon never claims a bundle compiles; only that command can.

---

## The GUI

Start it with `fabrizon gui`, `python -m fabrizon gui`, or by double-clicking `fabrizon_gui.pyw`. It starts a local server on `127.0.0.1`, prints a link containing a one-time token, and opens your browser.

| Option | Meaning |
|--------|---------|
| `--port N` | Use a fixed port (default: any free port) |
| `--no-browser` | Print the link but do not open a tab |

**Tabs**

- **1 · Analyze** — Drop a `.jar`, see mod info, injection points classified (mappable/review/blocked), Fabric API refs.
- **2 · Resolve** — Pick mappings file (Tiny v1/v2), Horizon source folder, target namespace. See ranked candidates with scores and reasons.
- **3 · Generate** — Output folder, optional `.hnmod` packaging, AI translation options (API key, base URL, model).
- **⚙ Settings** — Save API key, base URL, model, and default paths locally (persisted in browser).

Everything runs offline. The page has no external assets.

---

## Command line reference

Global: `fabrizon --version`, `fabrizon --help`. If not installed, prefix with `PYTHONPATH=src python -m`.

### `fabrizon analyze JAR [--json]`

Prints the feasibility report (or the full report as JSON). Exit code `2` with a message if the file is not a readable Fabric mod.

### `fabrizon resolve JAR [--mappings FILE] [--to NS] [--horizon DIR] [--json]`

| Flag | Meaning |
|------|---------|
| `--mappings FILE` | Tiny v1 or v2 mappings (`.tiny` or `.gz`). Required for jars with intermediary names |
| `--to NS` | Namespace to map into (default `named`; use the namespace name in your file's header) |
| `--horizon DIR` | Horizon source checkout to index for `fn` definitions |
| `--json` | Machine-readable output |

Without `--horizon` there is nothing to match against; targets are still mapped and the output says so.

### `fabrizon generate JAR --horizon DIR --out DIR [--mappings FILE] [--to NS] [--crate NAME] [--revision SHA] [--hnmod FILE] [--game VERSION] [--mixins-revision SHA] [--ai-api-key KEY] [--ai-base-url URL] [--ai-model NAME]`

| Flag | Meaning |
|------|---------|
| `--horizon DIR` | **Required.** Horizon source checkout |
| `--out DIR` | **Required.** Folder to write the bundle into |
| `--crate NAME` | Cargo target name used as the prefix of target IDs. Default `horizon_core` |
| `--revision SHA` | Exact 40-character Horizon commit written to `[compatibility] horizon_revision` |
| `--hnmod FILE` | Also package the bundle as a `.hnmod` |
| `--game VERSION` | Minecraft version for the `.hnmod` manifest (e.g. `26.3`) |
| `--mixins-revision SHA` | Exact 40-char horizon-mixins commit for the `.hnmod` |
| `--ai-api-key KEY` | NVIDIA API key for AI-assisted translation (or set `FABRIZON_NVIDIA_API_KEY` env) |
| `--ai-base-url URL` | OpenAI-compatible API base URL (default: NVIDIA) |
| `--ai-model NAME` | Model name for AI translation (default: `nvidia/nemotron-3-ultra-550b-a55b`) |

### `fabrizon package BUNDLE --out FILE.hnmod [--compatibility FILE] [--horizon DIR] [--game VERSION] [--horizon-revision SHA] [--mixins-revision SHA] [--hooks N] [--json]`

Package a generated bundle folder as a deterministic `.hnmod`.

### `fabrizon gui [--port N] [--no-browser]`

See [The GUI](#the-gui).

---

## Output formats

### `analyze --json`

Object with `mod_id`, `version`, `license`, `authors`, `entrypoints`, `intermediary_names`, `refmaps`, `asset_files`, `data_files`, `class_count`, `mixin_class_count`, `sides`, `fabric_api_refs`, `warnings`, `counts` (`mappable`/`review`/`blocked`) and `findings`.

### `resolve --json`

List of: `mixin`, `annotation`, `java_target`, `java_method`, `readable_target`, `readable_method`, `status`, `kind`, `member`, `side`, `candidates` (`path`, `file`, `line`, `score`, `why`, `crate`, `ret`, `params`, `target`) and `notes`.

### `generate` output folder

```
my-mod/
├── horizon-mixin.toml      only if at least one HEAD/RETURN hook was emitted
├── <injection_id>.rs       one helper per live injection (translated body or comments)
├── NOTICE.md               original authors + license, derivative-work reminder
├── TODO.md                 everything that needs a human, with reasons
└── BRIEF.md                translation brief: target sig, Java, recovered Rust, notes
```

### `.hnmod` (stage 5 output)

Deterministic zip file:

```
zoomify-2.17.0+mc26.2.hnmod
├── horizon-native.json       {"schema":1,"id":"zoomify","version":"2.17.0+mc26.2",
                               "game":"26.3","horizon":"ba6344a59cb9e755b730dcf02285fc0d33b97d3c",
                               "mixins":"d9c83d7096b7ea5b83678da2efdfd6161f74997e","hooks":3}
└── mixins/zoomify/
    ├── horizon-mixin.toml
    ├── modifyfovwithzoom_calculatefov.rs
    └── modifyhudfovwithzoom_calculatehudfov.rs
```

Only `.rs` and `.toml` under `mixins/<id>/` are included; `NOTICE.md`, `TODO.md` and `BRIEF.md` are working notes, not part of the mod.

---

## Architecture

```
fabrizon/
├── fabrizon_gui.pyw          double-click launcher
├── pyproject.toml            package metadata, `fabrizon` console script
├── .gitignore
├── src/fabrizon/
│   ├── __main__.py           `python -m fabrizon`
│   ├── cli.py                argparse entry point: analyze / resolve / generate / package / gui
│   ├── classfile.py          minimal Java class-file reader (annotations, class refs, bytecode)
│   ├── jar.py                Fabric jar reader: manifest, mixin configs, sides, assets/data
│   ├── analysis.py           annotation -> {status, horizon kind, note} classification
│   ├── report.py             text / JSON rendering of the report
│   ├── mappings.py           Tiny v1/v2 reader, class/method name mapping
│   ├── rustindex.py          lexical scan of a Horizon checkout for fns, impls, modules (crate-aware)
│   ├── resolve.py            selector parsing, ranking, resolution statuses
│   ├── javacode.py           bytecode decompiler: statements from Code attribute (stage 4, piece 1)
│   ├── translate.py          helper + bindings + BRIEF.md (stage 4, piece 2)
│   ├── ai_translate.py       optional LLM client for AI-assisted translation
│   ├── generate.py           horizon-mixins bundle writer (HEAD/RETURN) + NOTICE/TODO/BRIEF
│   ├── package.py            deterministic .hnmod zip (stage 5)
│   ├── fabric_events.py      Fabric API event -> Horizon hook mapping
│   ├── gui.py                local HTTP server, upload store, API endpoints
│   └── gui_page.py           the single-page UI (HTML/CSS/JS in one string)
└── tests/
    ├── classbuilder.py       builds synthetic class files and jars for tests
    ├── test_fabrizon.py      stage 1 (class parsing, jar reading, classification, CLI)
    ├── test_stage2.py        mappings, Rust index, matcher, `resolve` CLI
    ├── test_generate.py      bundle output, TOML validity, revision check
    └── test_gui.py           token/host checks, upload -> analyze -> resolve, error paths
```

Data flow:

```
read_jar → JarInfo → analyze → Report (list of Finding)
    → resolve (+ Mappings, RustFn index) → Resolution list
    → generate → Bundle → files / package → .hnmod
```

---

## GUI security model

The GUI exists to be convenient, but it is still a web server, so it is locked down:

- Binds to **`127.0.0.1` only**, never your network.
- A **random token** is generated each run and required (in the link and as an `X-Token` header). The page without it returns 403.
- Requests whose `Host` header is not `127.0.0.1:<port>` or `localhost:<port>` are rejected (defends against DNS rebinding).
- Uploads are capped at 512 MB and stored in a private temp folder that is **deleted when you stop the server**.
- Only the Horizon folder path you type is read from disk, and only for `.rs` files.
- Nothing is sent to the internet; the page has no external scripts, fonts or images.
- Analyzing a jar never executes it.

---

## Development and tests

```bash
python -m pytest -q          # 31 tests, standard library only
```

CI (`.github/workflows/test.yml`) runs them on Python 3.10 and 3.12.

`tests/classbuilder.py` writes class files and jars by hand because there was no `javac` or real mod available when this was built. That is also why **passing tests prove the parser and logic are consistent with themselves, not that they handle real mods**.

---

## Limitations

Read these before trusting a report.

- **Kind, not site.** `mappable` and `review` mean a horizon-mixins kind exists. Only `horizon-mixins plan`/`check` confirms a site is hookable and the bundle compiles.
- **Name matching is a guess.** Horizon was rewritten from scratch in Rust; its function and type names may not mirror Minecraft's Java names. Expect many `unresolved` and `ambiguous` results.
- **The Rust scan is lexical.** Macro-generated functions, `cfg`-gated code and unusual formatting can be missed (multi-line `impl` headers whose `{` is on a later line are not tracked). Only workspace members are indexed.
- **HEAD and RETURN only in stage 3.** All other kinds are listed, not generated.
- **Helper bodies are conservative.** Stage 4 translates only mechanically safe statements (primitives, arithmetic, `if`, locals, returns). Calls, field access, objects, generics become comments + `BRIEF.md` entries. The helper always compiles as a private `fn`; it may just be a no-op until filled in.
- **Parameter annotations are not read**, so `@Local` captures are not reported.
- **Fabric API is listed, not mapped.** Fabric API implements events with its own mixins; each event would need an event-to-site table.
- **Jar-in-jar is not analyzed.**
- **Dedicated servers:** Horizon's own docs say native mods are not built for dedicated servers yet.
- **Default crate name `horizon_core`** is a guess from horizon-mixins' examples. Verify against Horizon's `Cargo.toml`.
- **Docs move.** horizon-mixins and Horizon change fast; the tables here follow their documentation as of 2026-11-01.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `no fabric.mod.json at the root of the jar` | The file isn't a Fabric mod (Forge/NeoForge mods use different manifests), or it's a different archive. |
| Everything is `needs-mappings` | The jar uses intermediary names. Pass `--mappings` with a Tiny file that has an intermediary namespace (and a `named` one, or pass `--to` with your namespace name). |
| `namespace 'named' not in [...]` | Your Tiny file's header names its namespaces differently. Use `--to` with one of the names listed in the error. |
| Everything is `unresolved` | Either `--horizon` isn't set, it points at the wrong folder, or Horizon names differ from Java's. Open `resolve --json` and look at the notes. Use the candidates as search hints, not answers. |
| `generate` wrote no `horizon-mixin.toml` | No HEAD/RETURN hook resolved confidently. Read `TODO.md`. |
| `Horizon folder not found` | Paste the full path to the checkout (quotes are stripped). The GUI server reads it from *your* disk. |
| `horizon_revision must be an exact 40-character commit hash` | Use the full SHA, not a short hash or a branch name. |
| The browser says 403 | Open the exact link the terminal printed (it contains the token). It changes every run. |
| Does it modify my Horizon checkout? | No. It only reads `.rs` files. |
| Can it run a translated mod? | Not on its own. Stages 4 and 5 are needed, then Horizon's launcher builds the modded game. |

---

## Sources

Everything Fabrizon encodes about Horizon comes from these public pages (checked 2026-11-01). Re-read them; they change quickly, and where they and this tool disagree, the pages win.

- Horizon: https://github.com/horizon-rust/horizon
- Horizon releases: https://github.com/horizon-rust/horizon/releases
- Native mods (how bundles are built and pinned): https://github.com/horizon-rust/horizon/blob/main/docs/native-mods.md
- horizon-mixins: https://github.com/horizon-rust/horizon-mixins
- `horizon-mixin.toml` format: https://github.com/horizon-rust/horizon-mixins/blob/main/docs/mixin-api.md
- Mixin kind coverage and gaps: https://github.com/horizon-rust/horizon-mixins/blob/main/docs/spongepowered-feature-gaps.md
- Registry and official native mods: https://github.com/horizon-rust/horizon-mods
- Native mod template: https://github.com/horizon-rust/horizon-native-mod-template
- SpongePowered Mixin: https://github.com/SpongePowered/Mixin
- MixinExtras: https://github.com/LlamaLad7/MixinExtras
- Author support: https://ko-fi.com/melthedev

---

## Credits

- **Fabrizon** is made by **melthedev**. If it saves you time, you can [support me on Ko-fi](https://ko-fi.com/melthedev).
- [Horizon](https://github.com/horizon-rust/horizon) by ludovic111 and contributors, and [horizon-mixins](https://github.com/horizon-rust/horizon-mixins) by levzzz5154: the target this tool translates to. The mapping table is derived from their documentation.
- [SpongePowered Mixin](https://github.com/SpongePowered/Mixin) and [MixinExtras](https://github.com/LlamaLad7/MixinExtras): the source semantics.

---

MIT licensed. See `LICENSE`.
