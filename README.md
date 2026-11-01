<img src="assets/icon.svg" width="64" height="64" alt="">

<div align="center">

# Fabrizon

**Translate Fabric mods for [Horizon](https://github.com/horizon-rust/horizon).**

Drop in a Fabric mod `.jar`, get a feasibility report, candidate Horizon targets, and a ready-to-check horizon-mixins bundle.

Made by **melthedev** · [Support me on Ko-fi](https://ko-fi.com/melthedev) · MIT licensed

</div>

> **Unofficial.** Fabrizon is a community project. It is not made by, affiliated with, or endorsed by the Horizon project, Mojang or Microsoft. It contains no Minecraft code or assets.

> **Be honest about the state of it.** Stages 1 to 3 are built (stage 3 only partly). Stages 4 and 5 are not. **Nothing has been run on a real Fabric mod, real mappings or the real Horizon source yet.** Every output is a *candidate to verify*, never a promise. See [Status](#status) and [Limitations](#limitations).

---

## Table of contents

1. [What Fabrizon is](#what-fabrizon-is)
2. [Why it works this way](#why-it-works-this-way)
3. [Status](#status)
4. [Quick start](#quick-start)
5. [The GUI](#the-gui)
6. [Command line reference](#command-line-reference)
7. [Core concepts](#core-concepts)
8. [How each stage works](#how-each-stage-works)
9. [Output formats](#output-formats)
10. [Architecture and code map](#architecture-and-code-map)
11. [GUI security model](#gui-security-model)
12. [Development and tests](#development-and-tests)
13. [Limitations](#limitations)
14. [Troubleshooting and FAQ](#troubleshooting-and-faq)
15. [Roadmap](#roadmap)
16. [Licensing of translated mods](#licensing-of-translated-mods)
17. [AI disclosure](#ai-disclosure)
18. [Sources](#sources)
19. [Credits](#credits)

---

## What Fabrizon is

Horizon is Minecraft: Java Edition rewritten from scratch in Rust. Because it is native code, **Java mod jars cannot load in it**. Horizon's own route for code mods is *native mods*: small bundles (a `horizon-mixin.toml` plus Rust helper files) that a tool called [horizon-mixins](https://github.com/horizon-rust/horizon-mixins) applies to Horizon's own Rust source **before it is compiled**. The launcher then builds a modded game for the player.

Most Fabric mods change the game with **SpongePowered Mixin** annotations (`@Inject`, `@ModifyArg`, ...). horizon-mixins has counterparts for much of that vocabulary (HEAD, RETURN, BEFORE_CALL, MODIFY_ARG, WRAP_OPERATION, ...). Fabrizon is the bridge:

```
 Fabric mod .jar                                              horizon-mixins bundle
┌──────────────────┐   1 analyze    ┌──────────────┐  2 resolve   ┌───────────────┐  3 generate   ┌──────────────────────┐
│ fabric.mod.json  │ ─────────────▶ │ findings:    │ ───────────▶ │ candidate     │ ────────────▶ │ horizon-mixin.toml   │
│ mixin configs    │  read classes, │ mappable /   │  mappings +  │ Horizon Rust  │  HEAD hooks   │ helper .rs stubs     │
│ mixin .class     │  annotations   │ review /     │  Rust index  │ fn paths      │  live, rest   │ NOTICE.md  TODO.md   │
│ assets / data    │                │ blocked      │              │ (ranked)      │  in TODO.md   │                      │
└──────────────────┘                └──────────────┘              └───────────────┘               └──────────┬───────────┘
                                                                                                             │ 4 translate helpers (not built)
                                                                                                             │ 5 package .hnmod      (not built)
                                                                                                             ▼
                                                                                              horizon-mixins plan / check
```

It ships with a GUI (a local web page, no installs) and a CLI.

## Why it works this way

These are the design decisions, so you know what to trust and what not to.

- **It reads class files directly, with the standard library only.** Mixin annotations live in compiled `.class` files, so Fabrizon contains a small class-file reader (constant pool, annotations, class references). Nothing is executed or decompiled. That means: no Java needed, no dependencies, and analyzing an untrusted jar cannot run its code.
- **It classifies by *kind*, not by *site*.** "Does horizon-mixins have a hook of this kind?" is answerable from documentation. "Can this exact line of Horizon's Rust be hooked?" needs Horizon's pinned source. Stage 1 answers only the first question, which is why `mappable` is not a promise.
- **Name resolution is split into three small, testable pieces** (mappings reader, Rust indexer, matcher) because each one can be wrong in a different way, and you want to be able to see which.
- **It only emits what the docs fully specify.** horizon-mixins rejects unknown fields and bad bindings, so a guessed TOML would just fail `plan`. Fabrizon emits live injections for **HEAD hooks only** and puts everything else in `TODO.md` with the reason.
- **Helper bodies are stubs.** A Java handler body cannot be mechanically converted to Rust. Stage 4 will be AI-assisted and validated by `horizon-mixins check`; until then the stub says so.
- **Credit and licensing travel with the output.** Every bundle includes a `NOTICE.md` with the original authors and license, because a translation is a derivative work.
- **The GUI is a local web page** because it looks good, works the same on Windows and Linux, and needs nothing installed beyond Python.

## Status

| Stage | Command | What it does | State |
|---|---|---|---|
| 1 | `analyze` | Read a jar, classify every mixin injection point (mappable / review / blocked) | Built |
| 2 | `resolve` | Map Fabric targets through Tiny mappings, index a Horizon checkout, rank candidate Rust functions | Built |
| 3 | `generate` | Write a horizon-mixins bundle. Live injections for HEAD (incl. cancellable) and RETURN; the rest listed in `TODO.md` | Built |
| 4 | `generate` (with `--out`) | Decompile mixin handler bytecode; mechanically safe parts translated to Rust; rest commented + `BRIEF.md` | Built |
| 5 | `package` | Package the bundle folder as a deterministic `.hnmod` zip (sorted, fixed timestamp, 512 files / 64 MiB) | Built |

`python -m pytest -q` runs 31 tests (standard library only). Real-data verification (2026-11-01):

- Horizon `ba6344a59cb9e755b730dcf02285fc0d33b97d3c`, horizon-mixins `d9c83d7096b7ea5b83678da2efdfd6161f74997e` (0.6.0, schema 6)
- Yarn `1.21+build.9` (v2 tiny), Vein Mining jar, Zoomify jar
- `horizon-mixins plan` OK on the generated Zoomify bundle; `.hnmod` produced and read back

Limitations below apply; see the `TODO.md` / `BRIEF.md` a bundle produces.

## Quick start

**Requirements:** Python 3.10 or newer. No other dependencies.

```bash
unzip fabrizon.zip && cd fabrizon

# GUI (easiest): double-click fabrizon_gui.pyw, or:
# (see the install note below if `python -m fabrizon` can't find the package)
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

## The GUI

Start it with `fabrizon gui`, `python -m fabrizon gui`, or by double-clicking `fabrizon_gui.pyw`. It starts a local server on `127.0.0.1`, prints a link containing a one-time token, and opens your browser.

| Option | Meaning |
|---|---|
| `--port N` | Use a fixed port (default: any free port) |
| `--no-browser` | Print the link but do not open a tab |

**Screens**

- **Drop zone.** Drop a `.jar` anywhere on the page, or click to choose. The file is uploaded to a temporary folder on *your own machine* (never the internet).
- **1 · Analyze.** Mod id, version, license, authors, class and mixin counts, which side each mixin runs on, asset/data counts, whether intermediary names were detected, three big counters (mappable / needs review / blocked), a filterable table of every injection point with Horizon kind and notes, and the Fabric API classes used. **Export JSON** saves the full report.
- **2 · Resolve names.**
  - *Mappings file*: Tiny v1/v2 (`.tiny` or `.gz`). Needed when the jar uses `class_1234`-style names.
  - *Horizon source folder*: the path to your local Horizon checkout (typed, because the server is local).
  - *Target namespace*: usually `named`.
  - *Cargo target name* and *Horizon commit*: used by Generate (defaults `horizon_core`, commit optional).
  - **Resolve** shows each target with a status badge and ranked candidates with scores and reasons. **Export JSON** saves them.
  - **Generate bundle (.zip)** downloads the stage 3 output.
- Everything runs offline. The page has no external assets.

## Command line reference

Global: `fabrizon --version`, `fabrizon --help`. If not installed, prefix with `PYTHONPATH=src python -m`.

### `fabrizon analyze JAR [--json]`

Prints the feasibility report (or the full report as JSON). Exit code `2` with a message if the file is not a readable Fabric mod.

### `fabrizon resolve JAR [--mappings FILE] [--to NS] [--horizon DIR] [--json]`

| Flag | Meaning |
|---|---|
| `--mappings FILE` | Tiny v1 or v2 mappings (`.tiny` or `.gz`). Required for jars with intermediary names |
| `--to NS` | Namespace to map into (default `named`; use the namespace name in your file's header) |
| `--horizon DIR` | Horizon source checkout to index for `fn` definitions |
| `--json` | Machine-readable output |

Without `--horizon` there is nothing to match against; targets are still mapped and the output says so.

### `fabrizon generate JAR --horizon DIR --out DIR [--mappings FILE] [--to NS] [--crate NAME] [--revision SHA]`

| Flag | Meaning |
|---|---|
| `--horizon DIR` | **Required.** Horizon source checkout |
| `--out DIR` | **Required.** Folder to write the bundle into |
| `--crate NAME` | Cargo target name used as the prefix of target IDs. Default `horizon_core`, which is a guess taken from horizon-mixins' examples: check Horizon's `Cargo.toml` |
| `--revision SHA` | Exact 40-character Horizon commit written to `[compatibility] horizon_revision`. Validated; anything else is an error |
| `--mappings`, `--to` | Same as `resolve` |

### `fabrizon gui [--port N] [--no-browser]`

See [The GUI](#the-gui).

## Core concepts

**Fabric mod.** A `.jar` with `fabric.mod.json` at its root. Lists mixin config files, entrypoints, license and authors.

**SpongePowered Mixin.** A system where a mod ships small classes annotated with `@Mixin(TargetClass.class)` whose methods carry `@Inject`, `@ModifyArg`, etc. Fabric applies them to Minecraft's bytecode at launch. Fabrizon reads these annotations, never runs them.

**Mixin config.** A JSON file (e.g. `demo.mixins.json`) with a `package` and lists `mixins` (common), `client`, `server`. Fabrizon uses it to find which classes are mixins and which side each runs on. A manifest entry can also pin an environment.

**Intermediary and Yarn names.** Compiled Fabric mods refer to Minecraft by obfuscation-stable *intermediary* names (`class_1234`, `method_5678`). Humans use *named* mappings like Yarn. A **Tiny** file (v1 or v2) lists these name pairs per namespace. Fabrizon reads Tiny to turn `class_1234` into a readable name before looking for it in Horizon.

**Refmap.** A JSON file some mods ship that remaps mixin targets. If present, the report warns that targets may need remapping.

**Horizon native mod / horizon-mixins bundle.** A folder with `horizon-mixin.toml` and helper `.rs` files. horizon-mixins rewrites Horizon's Rust AST to call the helpers at specific *hook points*, then the game is compiled. Bundles are native code with the player's rights, **not sandboxed**.

**Target ID.** How horizon-mixins names a function: `crate::module::Type::function` (hyphens in the crate name become underscores). Free function: `fixture_game::entity::advance`. Method: `fixture_game::entity::Entity::tick`.

**Injection kinds** that exist in horizon-mixins: `HEAD` (including cancellable), `RETURN`, `BEFORE_CALL`, `AFTER_CALL`, `AFTER_ASSIGN`, `MODIFY_ARG`, `MODIFY_ARGS`, `MODIFY_CONSTANT`, `MODIFY_VARIABLE`, `MODIFY_EXPRESSION_VALUE`, `WRAP_OPERATION`, `OVERWRITE`, plus accessor/invoker bridges, support modules and per-instance state. **Not implemented upstream:** `REDIRECT`, `TAIL`, FIELD/NEW/JUMP sites, interface/soft-implements mixins. Always check the current docs; this moves quickly.

## How each stage works

### Stage 1: analyze

**Files:** `jar.py`, `classfile.py`, `analysis.py`, `report.py`

1. `jar.read_jar` opens the zip and requires `fabric.mod.json` (else `NotAFabricMod`). It parses the manifest, counts `assets/` and `data/` files, and counts nested jars in `META-INF/jars/` (warned, not analyzed).
2. For each mixin config in the manifest it reads `package`, `mixins`, `client`, `server`, `refmap`, and works out each mixin class's path and **side** (`common`, `client`, `server`). Missing configs or classes become warnings, not crashes.
3. Every `.class` is parsed by `classfile.parse_class`: the constant pool, class/field/method annotations (visible and invisible), and the set of class references. A bad class file becomes a warning. Classes referencing `net/fabricmc/fabric/api/...` are collected as Fabric API usage. Mixin classes whose strings contain `class_NNNN`/`method_NNNN`/`field_NNNN` set the *intermediary names* flag.
4. `analysis.analyze` walks each mixin class's methods and fields and turns each Mixin/MixinExtras annotation into one or more **findings**, each with a status, a horizon-mixins kind (if any), the side, the target class(es), the method selectors and a note.

**Classification table**

| Java annotation | Horizon kind | Status | Why |
|---|---|---|---|
| `@Inject` at `HEAD` | HEAD | mappable | Direct counterpart (`cancellable` is noted) |
| `@Inject` at `RETURN` | RETURN | mappable | Covers all exits. `ordinal` on RETURN (one specific return) is **blocked** |
| `@Inject` at `TAIL` | none | blocked | TAIL is missing; RETURN is not an alias |
| `@Inject` at `INVOKE` | BEFORE_CALL, or AFTER_CALL with `shift = AFTER` | review | Needs an exact syntax selector, ordinal and exact count; only whole statements, plain `let` initializers and block/function tails are hookable |
| `@Inject` at `INVOKE_ASSIGN` | AFTER_ASSIGN | review | Captures the stored result |
| `@Inject` at `CONSTANT` | MODIFY_CONSTANT | review | Exact runtime literals only |
| `@Inject` at `FIELD` / `NEW` / `JUMP` | none | blocked | Not implemented |
| any `@At` with `shift = BY` | none | blocked | Relative instruction offsets not implemented |
| other / custom `@At` | none | blocked | No counterpart |
| `@Overwrite` | OVERWRITE | review | Conflicts with every other hook on that function |
| `@ModifyArg` / `@ModifyArgs` | MODIFY_ARG / MODIFY_ARGS | review | Explicit index, same input/output type |
| `@ModifyConstant` | MODIFY_CONSTANT | review | Exact runtime literals only |
| `@ModifyVariable` | MODIFY_VARIABLE | review | Plain locals/params; limited STORE/LOAD forms |
| `@WrapOperation` | WRAP_OPERATION | review | Typed `FnOnce` continuation |
| `@ModifyExpressionValue` | MODIFY_EXPRESSION_VALUE | review | Exact syntax selector; runtime values only |
| `@ModifyReturnValue` | RETURN | review | Closest is RETURN with result replacement |
| `@Accessor` / `@Invoker` | bridge (GET/SET, INVOKE) | review | Owned, non-generic structs only |
| `@Unique` | `[[state]]` or `[[module]]` | review | Per-instance state needs explicit constructors |
| `@Redirect` | none | blocked | REDIRECT not implemented |
| `@Shadow`, `@Final`, `@Mutable`, `@Intrinsic` | none | blocked | No declarative equivalent (`@Shadow` may be hand-rewritable) |
| interface mixin, `@Implements` | none | blocked | Not implemented |
| unknown Mixin annotation | none | blocked | No documented counterpart |

Extra notes are attached for multiple target methods, wildcards (`*`), `@Slice`, and local captures. Structural annotations (`@Mixin`, `@At`, `@Slice`, `@Coerce`, ...) are ignored as they carry no behavior themselves.

**Why `mappable` is not a promise:** it means a kind exists and the common case is straightforward. Whether the site exists in Horizon's actual code is only checked in stages 2 and 3, and fully only by `horizon-mixins plan`.

### Stage 2: resolve

**Files:** `mappings.py`, `rustindex.py`, `resolve.py`

**2a. Mappings (`mappings.py`).** `parse_tiny` reads Tiny **v1** (`v1<TAB>ns1<TAB>ns2`, lines `CLASS`/`FIELD`/`METHOD`) and **v2** (`tiny<TAB>2<TAB>0<TAB>ns1...`, nested `c`/`m`/`f`). Parameters, locals and comments in v2 are ignored. `.gz` is supported. `map_class(name, to_ns)` searches every namespace for the name; `map_methods(name, to_ns, owner=...)` maps a method name and, when you pass the owner class, only accepts methods on that owner (the same intermediary name can exist on several classes). A method that maps to several names is reported.

**2b. Rust index (`rustindex.py`).** `index_tree` walks a checkout (skipping `target/`, `.git/`, `node_modules/`) and for every `.rs` file records each `fn` with: its **module path** (derived from the file path, `src/` and `lib`/`main`/`mod` stripped, plus inline `mod x { }` blocks), the **impl type** and **trait** it sits in (`impl Foo`, `impl Trait for Foo`, generics and `where` clauses handled), file and line. Comments and string literals are blanked first so `// fn fake()` and `"fn fake()"` are not indexed. This is a lexical scan, not a compiler: **macros, generated code and `cfg`-gated items can be missed or mis-scoped.**

**2c. Matching (`resolve.py`).** For each finding, per target class and method selector:

1. Parse the selector (`name`, `name(desc)ret`, or `Lowner;name(desc)ret`).
2. If mappings were given, map the class and method to the target namespace. Unmapped intermediary names produce a note. If the jar uses intermediary names and **no** mappings were given, the result is `needs-mappings`.
3. Rank every indexed `fn` (keeping candidates whose `fn` name matches the Java method at all):

| Signal | Points |
|---|---|
| `fn` name equals snake_case of the Java method (`tickServer` → `tick_server`) | +50 |
| `fn` name contains / is contained in it | +15 |
| `impl` type equals the Java class's simple name | +40 |
| `impl` type equals it ignoring case style | +35 |
| `impl` type resembles it | +10 |
| free `fn` in a module named after the class | +20 |

   The top 5 are kept, with the reasons listed.
4. **Status:** `resolved` if there is one candidate or the best leads the second by 30+ points; `ambiguous` if several are close; `unresolved` if there are none or names are still intermediary; `needs-mappings` as above.

These scores are heuristics tuned for readable names. They are why every result must be verified.

### Stage 3: generate

**File:** `generate.py`

For each *resolved* finding whose kind is **HEAD**, it writes one `[[injection]]` plus an empty helper. Everything else becomes a line in `TODO.md` with the reason:

| Case | Result |
|---|---|
| resolved + HEAD | live `[[injection]]`, helper stub |
| resolved + any other kind (RETURN, BEFORE_CALL, MODIFY_*, ...) | `TODO.md`: needs exact bindings/selectors/counts that a jar cannot supply |
| not resolved (ambiguous / unresolved / needs-mappings) | `TODO.md`: resolve by hand |
| client- or server-only mixin | live injection plus a `TODO.md` note to check the target's side/thread |

Details: mod id is the Fabric id slugged to lowercase-hyphen; version is copied (default `0.1.0`); `priority = 100`; injection ids are `<handler>-<method>` made unique; target IDs are `<crate>::<module>::<Type>::<fn>`; `bindings = []` because the stub takes no arguments (captured locals/parameters require typed bindings, which is exactly what stage 4 needs). `--revision` must be 40 hex characters.

**Why HEAD and RETURN:** horizon-mixins' API doc fully specifies both kinds with explicit bindings and no selector/count/ordinal fields. The other kinds require exact selectors, counts and typed bindings that cannot be derived from a Java jar, so emitting them would be a guess that fails `plan`.

### Stage 4: translate (helper bodies + BRIEF.md)

**Files:** `javacode.py`, `translate.py`

For each live injection (`HEAD` or `RETURN`), the resolved handler method is read from the jar:

1. **Decompile (`javacode.py`).** The handler's `Code` attribute is decoded into a structured list of statements. It rebuilds `if/else` from branches, primitives/arithmetic/string concat, locals and returns. Anything that needs Horizon's or Minecraft's API — calls, field access, object types, generic signatures — is left as a comment and marks the translation incomplete.

2. **Helper + bindings (`translate.py`).**  
   - The target's Rust signature (from `Candidate.ret` / `params`) provides the only reliable types.  
   - A private, synchronous, safe `fn` is emitted — the exact contract horizon-mixins requires (no attributes, no generics, no `self` receiver).  
   - For `RETURN`, the original result is bound as `$value` (the helper's `value` parameter).  
   - Translated statements are Rust; untranslated ones become `// TODO(stage 4): …` comments inside the body.  
   - `BRIEF.md` lists the target signature, the Java listing, the recovered Rust, and every note explaining why a statement was not translated.

The helper **always compiles**; it may just do nothing useful until the comments are filled in by a human or an AI.

### Stage 5: package (`.hnmod`)

**File:** `package.py`

`fabrizon package` turns the generated bundle folder into a registry-ready `.hnmod`:

- Reads `horizon-mixin.toml` for `mod.id` / `mod.version`.  
- Reads `compatibility.json` (or the `--horizon` checkout's `NATIVE_HOOKS_API`) for `game`, `horizon_revision`, `horizon_mixins_revision`, `hooks`.  
- Writes `horizon-native.json` (`schema: 1`, those six fields) and only `.rs` / `.toml` files under `mixins/<id>/`.  
- Deterministic zip: entries sorted, timestamp `(2026,1,1,0,0,0)`, mode `0o100644`, DEFLATE.  
- Limits: 512 files, 64 MiB total (the registry's limits).  
- `mod.id` must match `[a-z0-9_]+` (the registry's rule).

Output is byte-for-byte reproducible; the registry's SHA-256 check will be stable.

## Output formats

### `analyze --json`

An object with `mod_id`, `version`, `license`, `authors`, `entrypoints`, `intermediary_names`, `refmaps`, `asset_files`, `data_files`, `class_count`, `mixin_class_count`, `sides`, `fabric_api_refs`, `warnings`, `counts` (`mappable`/`review`/`blocked`) and `findings`, each with `mixin`, `member`, `annotation`, `status`, `horizon`, `side`, `targets`, `selectors`, `note`.

### `resolve --json`

A list of: `mixin`, `annotation`, `java_target`, `java_method`, `readable_target`, `readable_method`, `status`, `kind`, `member`, `side`, `candidates` (`path`, `file`, `line`, `score`, `why`) and `notes`.

### `generate` output folder

```
my-mod/
├── horizon-mixin.toml      only if at least one HEAD/RETURN hook was emitted
├── <injection_id>.rs       one helper per live injection (translated body or comments)
├── NOTICE.md               original authors + license, derivative-work reminder
├── TODO.md                 everything that needs a human, with reasons
└── BRIEF.md                translation brief: target sig, Java, recovered Rust, notes
```

Example `horizon-mixin.toml` (now includes `RETURN` with `$value` binding):

```toml
[mod]
id = "my-mod"
version = "2.0"
priority = 100

[compatibility]
horizon_revision = "0123456789abcdef0123456789abcdef01234567"

[[injection]]
id = "on-tick-tickserver"
target = "horizon_core::server::MinecraftServer::tick_server"
kind = "HEAD"
helper = "on_tick_tickserver.rs"
bindings = []

[[injection]]
id = "modify-fov-calculate"
target = "horizon_client_render::camera::Camera::calculate_fov"
kind = "RETURN"
helper = "modify_fov_calculate.rs"
bindings = [{ name = "value", ty = "f32", value = "$value" }]
```

Example helper (stage 4 body — translated parts are Rust, the rest are comments):

```rust
// Generated by Fabrizon (https://ko-fi.com/melthedev). Unofficial. Part of this body is recovered from bytecode; anything marked TODO needs Horizon's API.
// From Fabric mixin com/example/mixin/M#onTick (server side)
// Java target: net/minecraft/class_1234#method_5678
// Horizon target: server::MinecraftServer::tick_server (server/tick.rs:42)
// Not translated (see BRIEF.md): call `Zoomify.getZoomDivisor` has no known Horizon counterpart
fn on_tick_tickserver() {
    // // TODO(stage 4): Zoomify.getZoomDivisor(partialTicks)  // float
    // return (fov / /* getZoomDivisor(...) */);
}
```

### `.hnmod` (stage 5 output)

A deterministic zip file:

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

## Architecture and code map

```
fabrizon/
├── fabrizon_gui.pyw          double-click launcher
├── pyproject.toml            package metadata, `fabrizon` console script
├── src/fabrizon/
│   ├── classfile.py          minimal Java class-file reader (annotations, class refs, bytecode)
│   ├── jar.py                Fabric jar reader: manifest, mixin configs, sides, assets/data
│   ├── analysis.py           annotation -> {status, horizon kind, note} classification
│   ├── report.py             text / JSON rendering of the report
│   ├── mappings.py           Tiny v1/v2 reader, class/method name mapping
│   ├── rustindex.py          lexical scan of a Horizon checkout for fns, impls, modules (crate-aware)
│   ├── resolve.py            selector parsing, ranking, resolution statuses
│   ├── javacode.py           bytecode decompiler: statements from Code attribute (stage 4, piece 1)
│   ├── translate.py          helper + bindings + BRIEF.md (stage 4, piece 2)
│   ├── generate.py           horizon-mixins bundle writer (HEAD/RETURN) + NOTICE/TODO/BRIEF
│   ├── package.py            deterministic .hnmod zip (stage 5)
│   ├── gui.py                local HTTP server, upload store, API endpoints
│   ├── gui_page.py           the single-page UI (HTML/CSS/JS in one string)
│   ├── cli.py                argparse entry point: analyze / resolve / generate / package / gui
│   └── __main__.py           `python -m fabrizon`
└── tests/
    ├── classbuilder.py       builds synthetic class files and jars for tests
    ├── test_fabrizon.py      stage 1 (class parsing, jar reading, classification, CLI)
    ├── test_stage2.py        mappings, Rust index, matcher, `resolve` CLI
    ├── test_generate.py      bundle output, TOML validity, revision check
    └── test_gui.py           token/host checks, upload -> analyze -> resolve, error paths
```

Data flow: `read_jar` → `JarInfo` → `analyze` → `Report` (list of `Finding`) → `resolve` (+ `Mappings`, `RustFn` index) → `Resolution` list → `generate` → `Bundle` → files / `package` → `.hnmod`.

## GUI security model

The GUI exists to be convenient, but it is still a web server, so it is locked down:

- Binds to **`127.0.0.1` only**, never your network.
- A **random token** is generated each run and required (in the link and as an `X-Token` header). The page without it returns 403.
- Requests whose `Host` header is not `127.0.0.1:<port>` or `localhost:<port>` are rejected (defends against DNS rebinding).
- Uploads are capped at 512 MB and stored in a private temp folder that is **deleted when you stop the server**.
- Only the Horizon folder path you type is read from disk, and only for `.rs` files.
- Nothing is sent to the internet; the page has no external scripts, fonts or images.
- Analyzing a jar never executes it.

## Development and tests

```bash
python -m unittest discover -s tests          # 31 tests, standard library only
```

CI (`.github/workflows/test.yml`) runs them on Python 3.10 and 3.12. One TOML-validity test needs `tomllib` (Python 3.11+) and is skipped on 3.10.

`tests/classbuilder.py` writes class files and jars by hand because there was no `javac` or real mod available when this was built. That is also why **passing tests prove the parser and logic are consistent with themselves, not that they handle real mods**.

To add a mapping rule, edit `_SIMPLE` / `_inject` in `analysis.py` and add a test in `tests/test_fabrizon.py`. To tune matching, edit `rank` in `resolve.py` and add a case in `tests/test_stage2.py`.

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

## Troubleshooting and FAQ

**`no fabric.mod.json at the root of the jar`.** The file isn't a Fabric mod (Forge/NeoForge mods use different manifests), or it's a different archive.

**Everything is `needs-mappings`.** The jar uses intermediary names. Pass `--mappings` with a Tiny file that has an intermediary namespace (and a `named` one, or pass `--to` with your namespace name).

**`namespace 'named' not in [...]`.** Your Tiny file's header names its namespaces differently. Use `--to` with one of the names listed in the error.

**Everything is `unresolved`.** Either `--horizon` isn't set, it points at the wrong folder, or Horizon names differ from Java's. Open `resolve --json` and look at the notes. Use the candidates as search hints, not answers.

**`generate` wrote no `horizon-mixin.toml`.** No HEAD hook resolved confidently. Read `TODO.md`.

**`Horizon folder not found`.** Paste the full path to the checkout (quotes are stripped). The GUI server reads it from *your* disk.

**`horizon_revision must be an exact 40-character commit hash`.** Use the full SHA, not a short hash or a branch name.

**The browser says 403.** Open the exact link the terminal printed (it contains the token). It changes every run.

**Does it modify my Horizon checkout?** No. It only reads `.rs` files.

**Can it run a translated mod?** Not on its own. Stages 4 and 5 are needed, then Horizon's launcher builds the modded game.

## Roadmap

Completed (2026-11-01):
- Stage 4: conservative bytecode decompiler + helper/bindings + `BRIEF.md` (verified on Zoomify, `plan` passed)
- Stage 5: deterministic `.hnmod` packaging (verified on Zoomify)

Next:
1. More kinds in `generate` once their binding/selector contracts can be derived safely (BEFORE_CALL, MODIFY_*, OVERWRITE — each needs exact AST info from the target).
2. Fabric API event-to-site table; `@Local` capture support; jar-in-jar.
3. Content mods: route `assets/` and `data/` into Horizon's content-mod path.
4. GUI: show `BRIEF.md` per helper; inline helper editor; one-click `plan`/`check` button.

## Licensing of translated mods

Translating a mod makes a **derivative work**. Keep the original license and credit the original author in anything you publish, and only translate mods whose licenses allow it. Fabrizon writes a `NOTICE.md` with the original authors and license into every bundle and prints the license in reports, but it does **not** check that the license allows derivatives. That is on you. Horizon's registry also asks authors to confirm they have the rights to what they submit, including ports. Fabrizon itself is MIT licensed.

## AI disclosure

Fabrizon was written with the help of an AI assistant (Claude), directed and reviewed by the author. Generated bundles carry a header comment saying they were produced by Fabrizon. If an AI agent writes any part of translated Rust in stage 4, that must be disclosed in the output and in anything you submit, as Horizon's repositories mark AI-agent work openly.

## Sources

Everything Fabrizon encodes about Horizon comes from these public pages (checked 2026-11-01). Re-read them; they change quickly, and where they and this tool disagree, the pages win.

- Horizon: https://github.com/horizon-rust/horizon
- Horizon releases: https://github.com/horizon-rust/horizon/releases
- Native mods (how bundles are built and pinned): https://github.com/horizon-rust/horizon/blob/main/docs/native-mods.md
- Mods overview: https://github.com/horizon-rust/horizon/blob/main/docs/mods.md
- horizon-mixins: https://github.com/horizon-rust/horizon-mixins
- `horizon-mixin.toml` format: https://github.com/horizon-rust/horizon-mixins/blob/main/docs/mixin-api.md
- Mixin kind coverage and gaps: https://github.com/horizon-rust/horizon-mixins/blob/main/docs/spongepowered-feature-gaps.md
- Registry and official native mods: https://github.com/horizon-rust/horizon-mods
- Native mod template: https://github.com/horizon-rust/horizon-native-mod-template
- Docs PR on the bundle manifest: https://github.com/horizon-rust/horizon-site/pull/8
- SpongePowered Mixin: https://github.com/SpongePowered/Mixin
- MixinExtras: https://github.com/LlamaLad7/MixinExtras
- Author support: https://ko-fi.com/melthedev

## Credits

- **Fabrizon** is made by **melthedev**. If it saves you time, you can [support me on Ko-fi](https://ko-fi.com/melthedev).
- [Horizon](https://github.com/horizon-rust/horizon) by ludovic111 and contributors, and [horizon-mixins](https://github.com/horizon-rust/horizon-mixins) by levzzz5154: the target this tool translates to. The mapping table is derived from their documentation.
- [SpongePowered Mixin](https://github.com/SpongePowered/Mixin) and [MixinExtras](https://github.com/LlamaLad7/MixinExtras): the source semantics.

MIT licensed. See `LICENSE`.
