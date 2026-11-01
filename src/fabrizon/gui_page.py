"""The single-page UI served by `fabrizon gui`. No external assets, works offline."""

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fabrizon — Translate Fabric mods for Horizon</title>
<style>
:root{
  --bg:#0b0d12; --panel:#12151d; --panel2:#181c26; --line:#272c3e;
  --text:#e8ebf5; --mute:#848aa5;
  --accent:#6d7eff; --accent2:#a86dff;
  --ok:#38d9a9; --warn:#ffc35a; --bad:#ff6b7a;
  --ok-bg:#1a3d30; --warn-bg:#3d331a; --bad-bg:#3d1a1f;
  --radius:12px; --radius-sm:8px;
  --shadow:0 4px 24px rgba(0,0,0,.35);
  --shadow-sm:0 2px 8px rgba(0,0,0,.2);
  --transition:.15s ease;
}
@media (prefers-color-scheme:light){
  :root{
    --bg:#f3f4f9; --panel:#fff; --panel2:#f0f2f7; --line:#d5d9e3;
    --text:#1c1f2e; --mute:#686c7e;
    --accent:#4c5dff; --accent2:#8a4cff;
    --ok:#1aa36a; --warn:#d99600; --bad:#d03a42;
    --ok-bg:#e8f7ef; --warn-bg:#fff7e6; --bad-bg:#fdecec;
    --shadow:0 4px 24px rgba(0,0,0,.1);
    --shadow-sm:0 2px 8px rgba(0,0,0,.08);
  }
}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:var(--bg); color:var(--text);
  font:14px/1.55 system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale;
  min-height:100vh;
}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

/* Layout */
.wrap{
  max-width:1100px; margin:0 auto; padding:32px 24px 80px;
}
header{
  display:flex; align-items:center; gap:16px; margin-bottom:24px;
  padding-bottom:20px; border-bottom:1px solid var(--line);
}
.logo{
  width:52px; height:52px; border-radius:14px;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  display:grid; place-items:center; font-weight:800; font-size:24px; color:#fff;
  box-shadow:var(--shadow-sm);
}
h1{margin:0; font-size:26px; font-weight:700; letter-spacing:-.3px; background:linear-gradient(90deg,var(--text),var(--mute)); -webkit-background-clip:text; background-clip:text; color:transparent}
.sub{color:var(--mute); font-size:13.5px; margin-top:2px}
header .spacer{flex:1}
.version-badge{
  background:var(--panel2); border:1px solid var(--line); color:var(--mute);
  padding:4px 10px; border-radius:99px; font-size:11px; font-weight:600;
}

/* Cards */
.card{
  background:var(--panel); border:1px solid var(--line);
  border-radius:var(--radius); padding:20px; margin-bottom:16px;
  box-shadow:var(--shadow-sm);
}
.card h2{margin:0 0 16px; font-size:16px; font-weight:650}
.card h3{margin:0 0 10px; font-size:14px; font-weight:600; color:var(--mute)}

/* Drop Zone */
.drop{
  border:2px dashed var(--line); border-radius:var(--radius);
  padding:48px 24px; text-align:center; cursor:pointer;
  background:var(--panel); transition:var(--transition);
  position:relative; overflow:hidden;
}
.drop::before{
  content:''; position:absolute; inset:0;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  opacity:0; transition:var(--transition);
}
.drop:hover,.drop.over{
  border-color:var(--accent); background:var(--panel2);
}
.drop.over::before{opacity:.04}
.drop b{display:block; font-size:17px; margin-bottom:6px; font-weight:600}
.drop span{color:var(--mute); font-size:13.5px}
.drop input{position:absolute; inset:0; opacity:0; cursor:pointer}

/* Loaded File Card */
.loaded-card{
  display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; margin-bottom:16px;
}
.loaded-info b{font-size:15px}
.loaded-info .note{color:var(--mute); font-size:12px; margin-top:2px}

/* Tabs */
.tabs{
  display:flex; gap:8px; margin:0 0 24px; padding:4px;
  background:var(--panel2); border-radius:10px;
  border:1px solid var(--line);
}
.tab{
  flex:1; text-align:center; padding:10px 16px;
  border-radius:8px; border:0; background:transparent;
  color:var(--mute); font-weight:600; font-size:13.5px;
  cursor:pointer; transition:var(--transition);
}
.tab.on{
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  color:#fff; box-shadow:0 2px 8px rgba(109,126,255,.3);
}
.tab:not(.on):hover{color:var(--text)}

/* Buttons */
.btn{
  display:inline-flex; align-items:center; gap:8px;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  color:#fff; border:0; border-radius:10px;
  padding:12px 22px; font-weight:650; font-size:14px;
  cursor:pointer; transition:var(--transition);
  box-shadow:0 2px 10px rgba(109,126,255,.25);
}
.btn:hover:not(:disabled){transform:translateY(-1px); box-shadow:0 4px 16px rgba(109,126,255,.35)}
.btn:active:not(:disabled){transform:translateY(0)}
.btn:disabled{opacity:.5; cursor:not-allowed; transform:none; box-shadow:none}
.btn .spin{
  width:16px; height:16px; border:2.5px solid rgba(255,255,255,.3);
  border-top-color:#fff; border-radius:50%;
  animation:spin .7s linear infinite; display:inline-block;
}
@keyframes spin{to{transform:rotate(360deg)}}
.btn.ghost{
  background:var(--panel2); color:var(--text); border:1px solid var(--line);
  box-shadow:none;
}
.btn.ghost:hover:not(:disabled){background:var(--panel); border-color:var(--accent)}
.btn.wide{flex:1; justify-content:center}

/* Inputs */
label{display:block; font-weight:600; margin:16px 0 6px; font-size:13.5px}
.hint{display:block; color:var(--mute); font-size:12px; font-weight:400; margin-top:2px}
input[type=text], input[type=file], input[type=password]{
  width:100%; background:var(--panel2); border:1px solid var(--line);
  border-radius:10px; padding:12px 14px; color:var(--text); font:inherit;
  transition:var(--transition);
}
input[type=text]:focus, input[type=password]:focus{outline:none; border-color:var(--accent); box-shadow:0 0 0 3px rgba(109,126,255,.15)}
input[type=file]{padding:8px 12px; cursor:pointer}

/* Grid */
.grid{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
  gap:12px; margin-bottom:20px;
}
.stat{
  background:var(--panel2); border-radius:10px; padding:14px 16px;
  text-align:center; border:1px solid var(--line);
}
.stat .n{font-size:28px; font-weight:800; line-height:1.1}
.stat .l{color:var(--mute); font-size:12px; margin-top:4px}
.stat .n.ok{color:var(--ok)}
.stat .n.warn{color:var(--warn)}
.stat .n.bad{color:var(--bad)}

/* Key-Value */
.kv{
  display:grid; grid-template-columns:140px 1fr; gap:8px 16px;
  font-size:13.5px;
}
.kv > div:nth-child(odd){color:var(--mute)}
.kv > div:nth-child(even){color:var(--text); word-break:break-all}

/* Chips */
.chips{display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 16px}
.chip{
  padding:6px 14px; border-radius:99px; border:1px solid var(--line);
  background:var(--panel2); color:var(--mute);
  font-weight:600; font-size:12px; cursor:pointer;
  transition:var(--transition);
}
.chip:hover{background:var(--panel); border-color:var(--accent); color:var(--text)}
.chip.on{
  color:#fff; background:linear-gradient(135deg,var(--accent),var(--accent2));
  border-color:transparent; box-shadow:0 2px 8px rgba(109,126,255,.3);
}

/* Tables */
.table-wrap{overflow-x:auto; margin-top:8px}
table{width:100%; border-collapse:collapse; font-size:13px}
th{
  text-align:left; color:var(--mute); font-weight:600; font-size:11.5px;
  padding:10px 12px; text-transform:uppercase; letter-spacing:.5px;
  border-bottom:1px solid var(--line);
}
td{padding:12px; border-top:1px solid var(--line); vertical-align:top}
td:first-child{padding-left:12px} td:last-child{padding-right:12px}
tr:hover td{background:var(--panel2)}

code,.mono{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:12.5px; word-break:break-all;
}

/* Badges */
.badge{
  display:inline-flex; align-items:center; padding:3px 10px;
  border-radius:99px; font-size:11px; font-weight:700;
  text-transform:uppercase; letter-spacing:.3px; line-height:1.2;
}
.b-mappable,.b-resolved{background:var(--ok-bg); color:var(--ok); border:1px solid rgba(56,217,169,.25)}
.b-review,.b-ambiguous,.b-needs-mappings{background:var(--warn-bg); color:var(--warn); border:1px solid rgba(255,195,90,.25)}
.b-blocked,.b-unresolved{background:var(--bad-bg); color:var(--bad); border:1px solid rgba(255,107,122,.25)}
.b-pending{background:var(--panel2); color:var(--mute); border:1px solid var(--line)}

/* Candidate Details */
.cand{
  margin:8px 0 0; padding:10px 12px;
  background:var(--panel2); border:1px solid var(--line);
  border-radius:8px; font-size:12.5px;
  animation:slideDown .15s ease;
}
@keyframes slideDown{
  from{opacity:0; transform:translateY(-4px)}
  to{opacity:1; transform:translateY(0)}
}
.cand .path{font-weight:600; color:var(--text)}
.cand .meta{color:var(--mute); font-size:11.5px; margin-top:4px}
.cand .why{color:var(--accent); font-size:11.5px; margin-top:4px}

/* Notes */
.notes{margin-top:8px; display:flex; flex-direction:column; gap:4px}
.note{
  color:var(--mute); font-size:12px; padding:8px 10px;
  background:var(--panel2); border-radius:6px; border-left:3px solid var(--accent);
}

/* Error Box */
.err{
  background:var(--bad-bg); border:1px solid rgba(255,107,122,.3);
  color:var(--bad); padding:14px 16px; border-radius:10px;
  margin-bottom:20px; white-space:pre-wrap; font-size:13px;
  animation:slideDown .2s ease;
}

/* Results Summary */
.results-summary{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(100px,1fr));
  gap:10px; margin-bottom:16px;
}
.summary-badge{
  display:flex; flex-direction:column; align-items:center; gap:4px;
  padding:12px; background:var(--panel2); border:1px solid var(--line);
  border-radius:10px;
}
.summary-badge .count{font-size:22px; font-weight:800}
.summary-badge .label{font-size:11.5px; color:var(--mute); text-transform:uppercase; letter-spacing:.3px}

/* Empty State */
.empty{
  text-align:center; padding:48px 24px; color:var(--mute);
}
.empty svg{width:64px; height:64px; margin-bottom:16px; opacity:.5}
.empty h3{margin:0 0 8px; font-size:16px; color:var(--text)}
.empty p{margin:0; font-size:13.5px}

/* Footer */
footer{
  margin-top:40px; padding-top:24px; border-top:1px solid var(--line);
  color:var(--mute); font-size:12.5px; text-align:center;
}
footer a{font-weight:600}

/* Toast */
.toast-container{
  position:fixed; bottom:24px; right:24px; z-index:1000;
  display:flex; flex-direction:column; gap:8px;
}
.toast{
  padding:14px 18px; border-radius:10px; font-size:13px;
  background:var(--panel); border:1px solid var(--line);
  box-shadow:var(--shadow); display:flex; align-items:center; gap:10px;
  animation:slideIn .25s ease; max-width:360px;
}
.toast.ok{border-left:4px solid var(--ok)}
.toast.err{border-left:4px solid var(--bad)}
.toast.warn{border-left:4px solid var(--warn)}
@keyframes slideIn{from{opacity:0; transform:translateX(20px)}to{opacity:1; transform:translateX(0)}}

/* Settings Tab */
.settings-grid{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
  gap:16px; margin-bottom:16px;
}
.setting-group{
  background:var(--panel2); border:1px solid var(--line);
  border-radius:10px; padding:16px;
}
.setting-group h3{margin:0 0 12px; font-size:13px; color:var(--mute); text-transform:uppercase; letter-spacing:.5px}
.setting-row{display:flex; flex-direction:column; gap:6px; margin-bottom:12px}
.setting-row label{margin:0; font-size:12px; font-weight:600; color:var(--text)}
.setting-row .hint{font-size:11px; color:var(--mute); margin-top:2px}
.setting-row input[type=text], .setting-row input[type=password]{
  background:var(--panel); border:1px solid var(--line);
  border-radius:8px; padding:10px 12px; color:var(--text); font:inherit;
}
.setting-row input[type=text]:focus, .setting-row input[type=password]:focus{
  outline:none; border-color:var(--accent); box-shadow:0 0 0 3px rgba(109,126,255,.15)
}
.setting-actions{display:flex; align-items:center; gap:12px; margin-top:12px}
.status-indicator{display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border-radius:6px; font-size:12px; font-weight:600}
.status-indicator.ok{background:var(--ok-bg); color:var(--ok); border:1px solid rgba(56,217,169,.25)}
.status-indicator.warn{background:var(--warn-bg); color:var(--warn); border:1px solid rgba(255,195,90,.25)}
.status-indicator.err{background:var(--bad-bg); color:var(--bad); border:1px solid rgba(255,107,122,.25)}

.row{display:flex; align-items:center}
.hide{display:none !important}

/* Responsive */
@media (max-width:768px){
  .wrap{padding:24px 16px 60px}
  .kv{grid-template-columns:100px 1fr}
  .grid{grid-template-columns:repeat(2,1fr)}
  .stat .n{font-size:22px}
  th,td{padding:10px 8px}
  .tabs{flex-wrap:wrap}
}
</style></head>
<body>
<div class="wrap">
<header>
  <div class="logo">F</div>
  <div>
    <h1>Fabrizon</h1>
    <div class="sub">Translate Fabric mods for Horizon · unofficial</div>
  </div>
  <div class="spacer"></div>
  <span class="version-badge" id="versionBadge">v0.0.0</span>
</header>

<div id="err" class="err hide"></div>
<div id="toasts" class="toast-container"></div>

<!-- Tabs are always accessible -->
<div class="tabs" role="tablist" aria-label="Pipeline steps">
  <div class="tab on" data-t="analyze" role="tab" aria-selected="true">1 · Analyze</div>
  <div class="tab" data-t="resolve" role="tab" aria-selected="false">2 · Resolve</div>
  <div class="tab" data-t="generate" role="tab" aria-selected="false">3 · Generate</div>
  <div class="tab" data-t="settings" role="tab" aria-selected="false">⚙ Settings</div>
</div>

<!-- Step 1: Analyze -->
<section id="t-analyze" role="tabpanel" aria-labelledby="tab-analyze">
  <div id="dropSection">
    <div id="drop" class="drop" role="button" tabindex="0" aria-label="Choose a Fabric mod jar">
      <b>Drop a Fabric mod <code>.jar</code> here</b>
      <span>or click to choose · files never leave your computer</span>
      <input id="fileInput" type="file" accept=".jar,.zip" class="hide" aria-hidden="true">
    </div>
  </div>

  <div id="loadedSection" class="hide">
    <div class="card loaded-card">
      <div class="loaded-info">
        <b id="fileName"></b>
        <div class="note" id="fileSize"></div>
      </div>
      <button class="btn ghost" id="swapBtn">Choose another mod</button>
    </div>
    <div class="row" style="margin-bottom:16px; gap:12px; flex-wrap:wrap">
      <button class="btn wide" id="runAnalyze"><span class="spin hide"></span>Re-run Analysis</button>
      <button class="btn ghost hide" id="exportAnalyze">Export JSON</button>
    </div>
    <div id="outAnalyze"></div>
  </div>
</section>

<!-- Step 2: Resolve -->
<section id="t-resolve" class="hide" role="tabpanel" aria-labelledby="tab-resolve">
  <div class="card">
    <h3>Mappings</h3>
    <div class="row" style="gap:12px; flex-wrap:wrap; align-items:center; margin-bottom:12px">
      <div style="flex:1; min-width:240px; background:var(--panel2); padding:12px 14px; border-radius:8px; border:1px solid var(--line)">
        <b style="color:var(--ok); display:block; margin-bottom:2px">✨ Auto-Mappings Active</b>
        <span class="hint" id="mapStatusText" style="margin:0">Fabric Yarn mappings will be downloaded/cached automatically based on mod dependencies.</span>
      </div>
      <button class="btn ghost" id="pickMap" style="white-space:nowrap">Choose custom .tiny…</button>
      <input id="mapFile" type="file" accept=".tiny,.gz" class="hide" aria-hidden="true">
    </div>

    <label>Horizon source folder <span class="hint">Path to your local Horizon checkout on this computer (auto-detected if available).</span></label>
    <input type="text" id="horizon" placeholder="C:\path\to\horizon   or   /home/you/horizon">

    <div class="grid" style="margin-top:12px; margin-bottom:0">
      <div>
        <label>Target namespace <span class="hint">Usually <code>named</code>.</span></label>
        <input type="text" id="ns" value="named">
      </div>
      <div>
        <label>Cargo target name <span class="hint">Prefix for target IDs, usually <code>horizon_core</code>.</span></label>
        <input type="text" id="crate" value="horizon_core">
      </div>
    </div>

    <label>Horizon commit <span class="hint">Optional exact 40-character commit hash for <code>[compatibility]</code>.</span></label>
    <input type="text" id="rev" placeholder="ba6344a59cb9e755b730dcf02285fc0d33b97d3c" style="max-width:380px">

    <div class="row" style="margin-top:20px; gap:10px; flex-wrap:wrap">
      <button class="btn wide" id="runResolve"><span class="spin hide"></span>Resolve Names</button>
      <button class="btn ghost hide" id="exportResolve">Export JSON</button>
    </div>
  </div>
  <div id="outResolve"></div>
</section>

<!-- Step 3: Generate -->
<section id="t-generate" class="hide" role="tabpanel" aria-labelledby="tab-generate">
  <div class="card">
    <h3>Bundle Options</h3>
    <div class="grid" style="margin-top:8px">
      <div>
        <label>Output folder <span class="hint">Where to write the bundle on disk (optional).</span></label>
        <input type="text" id="outDir" placeholder="/path/to/output">
      </div>
      <div>
        <label>Package as <code>.hnmod</code> <span class="hint">Also create a registry-ready zip.</span></label>
        <input type="text" id="hnmodPath" placeholder="/path/to/mod.hnmod (optional)">
      </div>
      <div>
        <label>Minecraft version <span class="hint">For .hnmod manifest (e.g. <code>26.3</code>).</span></label>
        <input type="text" id="gameVer" placeholder="26.3" style="max-width:180px">
      </div>
      <div>
        <label>horizon-mixins revision <span class="hint">Optional 40-char commit for the .hnmod.</span></label>
        <input type="text" id="mixinsRev" placeholder="d9c83d7096b7ea5b83678da2efdfd6161f74997e" style="max-width:360px">
      </div>
    </div>

    <h3>AI Translation (Optional)</h3>
    <span class="hint" style="margin-bottom:12px">Fill complex Java handler bodies using an LLM (uses settings configured in ⚙ Settings tab).</span>
    <div class="grid" style="margin-top:8px">
      <div>
        <label>API Key</label>
        <input type="password" id="genAiKey" placeholder="Synced from Settings">
      </div>
      <div>
        <label>Base URL</label>
        <input type="text" id="genAiBase" value="https://integrate.api.nvidia.com/v1">
      </div>
      <div>
        <label>Model</label>
        <input type="text" id="genAiModel" value="nvidia/nemotron-3-ultra-550b-a55b">
      </div>
    </div>

    <div class="row" style="margin-top:20px; gap:10px; flex-wrap:wrap">
      <button class="btn wide" id="runGenerate"><span class="spin hide"></span>Generate Bundle</button>
    </div>
  </div>
  <div id="outGenerate"></div>
</section>

<!-- Step 4: Settings -->
<section id="t-settings" class="hide" role="tabpanel" aria-labelledby="tab-settings">
  <div class="card">
    <h2>⚙ Fabrizon Settings</h2>
    <p class="hint" style="margin-bottom:20px; font-size:13px">Configure your API key and default preferences. Settings are saved locally in your browser and used automatically across runs.</p>

    <div class="settings-grid">
      <div class="setting-group">
        <h3>AI Translation API</h3>
        <div class="setting-row">
          <label>API Key <span class="hint">NVIDIA API or OpenAI-compatible key.</span></label>
          <input type="password" id="settingsAiKey" placeholder="nvapi-... or sk-..." autocomplete="off">
        </div>
        <div class="setting-row">
          <label>Base URL <span class="hint">Default: NVIDIA API endpoint.</span></label>
          <input type="text" id="settingsAiBase" value="https://integrate.api.nvidia.com/v1">
        </div>
        <div class="setting-row">
          <label>Model <span class="hint">Default: Nemotron 3 Ultra (or Nemotron 3.5 Lightning).</span></label>
          <input type="text" id="settingsAiModel" value="nvidia/nemotron-3-ultra-550b-a55b">
        </div>
        <div class="setting-actions">
          <button class="btn ghost" id="testAi" type="button">Test Connection</button>
          <span class="status-indicator hide" id="aiStatus"></span>
        </div>
      </div>

      <div class="setting-group">
        <h3>Default Paths & Targets</h3>
        <div class="setting-row">
          <label>Horizon Source Folder <span class="hint">Path to your local Horizon source checkout.</span></label>
          <input type="text" id="defHorizon" placeholder="C:\path\to\horizon or /home/you/horizon">
        </div>
        <div class="setting-row">
          <label>Target Namespace <span class="hint">Usually <code>named</code>.</span></label>
          <input type="text" id="defNs" value="named" style="max-width:240px">
        </div>
        <div class="setting-row">
          <label>Cargo Target Name <span class="hint">Prefix for target IDs, usually <code>horizon_core</code>.</span></label>
          <input type="text" id="defCrate" value="horizon_core" style="max-width:240px">
        </div>
        <div class="setting-row">
          <label>Minecraft Version <span class="hint">For .hnmod manifest (e.g. <code>26.3</code>).</span></label>
          <input type="text" id="defGame" value="26.3" style="max-width:180px">
        </div>
        <div class="setting-row">
          <label>horizon-mixins Revision <span class="hint">40-character commit for .hnmod.</span></label>
          <input type="text" id="defMixinsRev" placeholder="d9c83d7096b7ea5b83678da2efdfd6161f74997e">
        </div>
      </div>
    </div>

    <div class="row" style="margin-top:20px; gap:12px">
      <button class="btn" id="saveSettingsBtn" type="button">Save Settings</button>
    </div>
  </div>
</section>

<footer>
  Made by <b>melthedev</b> · <a href="https://ko-fi.com/melthedev" target="_blank" rel="noopener">Support on Ko-fi</a><br>
  Not affiliated with the Horizon project, Mojang or Microsoft.
  Results are candidates: run <code>horizon-mixins plan</code> and <code>check</code> on the pinned Horizon source before trusting a bundle.
</footer>
</div>

<script>
/* ===== Core Utilities ===== */
const T = new URLSearchParams(location.search).get('t') || '';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
const size = n => n > 1048576 ? (n/1048576).toFixed(1)+' MB' : Math.max(1, Math.round(n/1024))+' KB';

let jarId = null, mapId = null, lastAnalyze = null, lastResolve = null;

/* ===== Toast System ===== */
function toast(message, type='info'){
  const c = $('toasts') || (()=>{const d=document.createElement('div');d.id='toasts';d.className='toast-container';document.body.appendChild(d);return d})();
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = message;
  c.appendChild(t);
  setTimeout(()=>{t.style.animation='slideIn .25s ease reverse'; setTimeout(()=>t.remove(),250)}, 4000);
}

/* ===== API ===== */
async function api(path, opts={}){
  const r = await fetch(path, {...opts, headers:{'X-Token':T, ...(opts.headers||{})}});
  let d; try{d=await r.json()}catch{d={error:'Bad response from server'}}
  if(!r.ok || d.error) throw new Error(d.error || 'HTTP '+r.status);
  return d;
}
async function upload(file, kind){
  const d = await api('/api/upload?kind='+kind+'&name='+encodeURIComponent(file.name), {method:'POST', body:file});
  return d.id;
}

/* ===== Error Display ===== */
function err(m){ const e=$('err'); e.textContent=m||''; e.classList.toggle('hide', !m); }

/* ===== UI Helpers ===== */
function busy(btn, on, txt){
  btn.disabled = on;
  if(on){
    btn.dataset.orig = btn.innerHTML;
    btn.innerHTML = '<span class="spin"></span> ' + txt;
  }else{
    btn.innerHTML = btn.dataset.orig || btn.textContent;
  }
}
function download(name, obj){
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([JSON.stringify(obj,null,2)],{type:'application/json'}));
  a.download=name; a.click();
}

/* ===== File Handling ===== */
function handleFile(f){
  if(!f) return;
  err('');
  upload(f, 'jar').then(id=>{
    jarId = id;
    $('fileName').textContent = f.name;
    $('fileSize').textContent = size(f.size);
    $('dropSection').classList.add('hide');
    $('loadedSection').classList.remove('hide');
    clearResults();
    runAnalyze();
  }).catch(e=>err(e.message));
}

const drop = $('drop');
drop.onclick = () => $('fileInput').click();
$('swapBtn').onclick = () => $('fileInput').click();
$('fileInput').onchange = e => handleFile(e.target.files[0]);

['dragover','dragenter'].forEach(ev => document.addEventListener(ev, e => {e.preventDefault(); drop.classList.add('over')}));
['dragleave','drop'].forEach(ev => document.addEventListener(ev, e => {e.preventDefault(); drop.classList.remove('over')}));
document.addEventListener('drop', e => {const f=e.dataTransfer.files[0]; if(f) handleFile(f)});

/* ===== Tabs Switching ===== */
document.querySelectorAll('.tab').forEach(t => t.onclick = () => {
  document.querySelectorAll('.tab').forEach(x => {
    x.classList.toggle('on', x===t);
    x.setAttribute('aria-selected', x===t);
  });
  const target = t.dataset.t;
  $('t-analyze').classList.toggle('hide', target!=='analyze');
  $('t-resolve').classList.toggle('hide', target!=='resolve');
  $('t-generate').classList.toggle('hide', target!=='generate');
  $('t-settings').classList.toggle('hide', target!=='settings');
});

/* ===== Mappings File ===== */
$('pickMap').onclick = () => $('mapFile').click();
$('mapFile').onchange = async e => {
  const f = e.target.files[0]; if(!f) return; err('');
  try{
    mapId = await upload(f, 'map');
    $('mapStatusText').textContent = 'Custom file: ' + f.name + ' (' + size(f.size) + ')';
    toast('Custom mappings uploaded', 'ok');
  }catch(x){err(x.message)}
};

/* ===== Settings System ===== */
function loadSettings(){
  try{
    const s = JSON.parse(localStorage.getItem('fabrizon_settings') || '{}');
    if(s.aiKey) { $('settingsAiKey').value = s.aiKey; $('genAiKey').value = s.aiKey; }
    if(s.aiBase) { $('settingsAiBase').value = s.aiBase; $('genAiBase').value = s.aiBase; }
    if(s.aiModel) { $('settingsAiModel').value = s.aiModel; $('genAiModel').value = s.aiModel; }
    if(s.defHorizon) { $('defHorizon').value = s.defHorizon; $('horizon').value = s.defHorizon; }
    if(s.defNs) { $('defNs').value = s.defNs; $('ns').value = s.defNs; }
    if(s.defCrate) { $('defCrate').value = s.defCrate; $('crate').value = s.defCrate; }
    if(s.defGame) { $('defGame').value = s.defGame; $('gameVer').value = s.defGame; }
    if(s.defMixinsRev) { $('defMixinsRev').value = s.defMixinsRev; $('mixinsRev').value = s.defMixinsRev; }
  }catch{}

  // Auto-detect Horizon source checkout if not set
  if(!$('defHorizon').value.trim()){
    api('/api/system_info').then(info => {
      if(info && info.horizon && !$('defHorizon').value.trim()){
        $('defHorizon').value = info.horizon;
        $('horizon').value = info.horizon;
      }
    }).catch(()=>{});
  }
}

function saveSettings(silent=false){
  const s = {
    aiKey: $('settingsAiKey').value.trim(),
    aiBase: $('settingsAiBase').value.trim() || 'https://integrate.api.nvidia.com/v1',
    aiModel: $('settingsAiModel').value.trim() || 'nvidia/nemotron-3-ultra-550b-a55b',
    defHorizon: $('defHorizon').value.trim(),
    defNs: $('defNs').value.trim() || 'named',
    defCrate: $('defCrate').value.trim() || 'horizon_core',
    defGame: $('defGame').value.trim() || '26.3',
    defMixinsRev: $('defMixinsRev').value.trim(),
  };
  localStorage.setItem('fabrizon_settings', JSON.stringify(s));

  // Sync to generate form
  $('genAiKey').value = s.aiKey;
  $('genAiBase').value = s.aiBase;
  $('genAiModel').value = s.aiModel;
  if(s.defHorizon) $('horizon').value = s.defHorizon;
  if(s.defNs) $('ns').value = s.defNs;
  if(s.defCrate) $('crate').value = s.defCrate;
  if(s.defGame) $('gameVer').value = s.defGame;
  if(s.defMixinsRev) $('mixinsRev').value = s.defMixinsRev;

  if(!silent) toast('Settings saved successfully', 'ok');
  return s;
}

$('saveSettingsBtn').onclick = () => saveSettings(false);

['settingsAiKey','settingsAiBase','settingsAiModel','defHorizon','defNs','defCrate','defGame','defMixinsRev'].forEach(id=>{
  const el = $(id); if(el) el.onchange = () => saveSettings(true);
});

async function testAiConnection(){
  const btn = $('testAi');
  const status = $('aiStatus');
  const key = $('settingsAiKey').value.trim();
  const base = $('settingsAiBase').value.trim() || 'https://integrate.api.nvidia.com/v1';
  const model = $('settingsAiModel').value.trim() || 'nvidia/nemotron-3-ultra-550b-a55b';
  if(!key){
    status.textContent='Enter API key first';
    status.className='status-indicator warn';
    status.classList.remove('hide');
    return;
  }
  busy(btn, true, 'Testing…');
  status.classList.add('hide');
  try{
    const r = await api('/api/test_ai', {
      method:'POST',
      body:JSON.stringify({key, base, model})
    });
    status.textContent = r.message || 'Connected OK';
    status.className = 'status-indicator ok';
    status.classList.remove('hide');
    toast('API connection successful', 'ok');
  }catch(e){
    status.textContent = e.message;
    status.className = 'status-indicator err';
    status.classList.remove('hide');
    toast('API test error: '+e.message, 'err');
  }finally{
    busy(btn, false);
  }
}
$('testAi').onclick = testAiConnection;

/* ===== Clear Results ===== */
function clearResults(){
  $('outAnalyze').innerHTML = '';
  $('outResolve').innerHTML = '';
  $('outGenerate').innerHTML = '';
  $('exportAnalyze').classList.add('hide');
  $('exportResolve').classList.add('hide');
  lastAnalyze = lastResolve = null;
}

/* ===== Step 1: Analyze ===== */
async function runAnalyze(){
  if(!jarId) { toast('Drop a mod jar first', 'warn'); return; }
  err(''); busy($('runAnalyze'), true, 'Analyzing…');
  try{
    const r = await api('/api/analyze', {method:'POST', body:JSON.stringify({id:jarId})});
    lastAnalyze = r; renderAnalyze(r); $('exportAnalyze').classList.remove('hide');
  }catch(e){err(e.message)}
  finally{busy($('runAnalyze'), false);}
}
$('runAnalyze').onclick = runAnalyze;
$('exportAnalyze').onclick = () => download('fabrizon-analysis.json', lastAnalyze);

let analyzeFilter = 'all';
function renderAnalyze(r){
  const c = r.counts, f = r.findings;
  let h = `
    <div class="card">
      <h2>${esc(r.mod_id)} ${esc(r.version)}</h2>
      <div class="kv">
        <div>License</div><div>${esc(typeof r.license==='object'?JSON.stringify(r.license):r.license||'not declared')}</div>
        <div>Authors</div><div>${esc((r.authors||[]).join(', ')||'unknown')}</div>
        <div>Classes</div><div>${r.class_count} (${r.mixin_class_count} mixin classes)</div>
        <div>Sides</div><div>common ${r.sides.common} · client ${r.sides.client} · server ${r.sides.server}</div>
        <div>Content</div><div>${r.asset_files} assets, ${r.data_files} data files</div>
        <div>Names</div><div>${r.intermediary_names?'<span class="badge b-review">intermediary (auto-resolved with Yarn)</span>':'<span class="badge b-ok">readable</span>'}</div>
      </div>
    </div>
    <div class="grid">
      <div class="stat"><div class="n ok">${c.mappable}</div><div class="l">Mappable</div></div>
      <div class="stat"><div class="n warn">${c.review}</div><div class="l">Needs review</div></div>
      <div class="stat"><div class="n bad">${c.blocked}</div><div class="l">Blocked</div></div>
    </div>`;
  (r.warnings||[]).forEach(w => h += `<div class="err" style="background:var(--warn-bg);border-color:var(--warn);color:var(--warn)">${esc(w)}</div>`);

  h += `<div class="card">
    <h2>Injection Points</h2>
    <div class="chips">${['all','mappable','review','blocked'].map(k=>`<span class="chip ${analyzeFilter===k?'on':''}" data-f="${k}">${k}</span>`).join('')}</div>`;

  const rows = f.filter(x => analyzeFilter==='all' || x.status===analyzeFilter);
  if(rows.length){
    h += `<div class="table-wrap"><table><thead><tr><th>Status</th><th>Mixin / Member</th><th>Target</th><th>Horizon Kind</th><th>Note</th></tr></thead><tbody>`;
    rows.forEach(x => {
      const mixinShort = x.mixin.split('/').pop();
      const targets = (x.targets||[]).map(t=>t.split('/').pop()).join(', ') || '-';
      const selectors = (x.selectors||[]).join(', ') || '-';
      h += `<tr>
        <td><span class="badge b-${x.status}">${x.status}</span></td>
        <td class="mono">${esc(mixinShort)}<br><span class="note">${esc(x.member)} · ${esc(x.annotation)} · ${esc(x.side)}</span></td>
        <td class="mono">${esc(targets)}<br><span class="note">${esc(selectors)}</span></td>
        <td>${esc(x.horizon||'-')}</td>
        <td class="note" style="max-width:280px">${esc(x.note)}</td>
      </tr>`;
    });
    h += `</tbody></table></div>`;
  }else{
    h += `<div class="empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/><path d="M14 11a1 1 0 10-2 0 1 1 0 002 0z"/></svg><h3>No injection points</h3><p>Try adjusting the filter or check if this mod uses mixins.</p></div>`;
  }
  h += `</div>`;

  if((r.fabric_api_refs||[]).length){
    h += `<div class="card"><h2>Fabric API References</h2><span class="hint">${r.fabric_api_refs.length} classes referenced</span>
      <div class="mono" style="margin-top:8px; max-height:200px; overflow:auto">${r.fabric_api_refs.map(esc).join('<br>')}</div></div>`;
  }

  $('outAnalyze').innerHTML = h;
  $('outAnalyze').querySelectorAll('.chip').forEach(ch => ch.onclick = () => {analyzeFilter = ch.dataset.f; renderAnalyze(r)});
}

/* ===== Step 2: Resolve ===== */
$('runResolve').onclick = async () => {
  if(!jarId){ toast('Upload a mod jar on Analyze tab first', 'warn'); return; }
  err(''); busy($('runResolve'), true, 'Resolving…');
  try{
    const r = await api('/api/resolve', {method:'POST', body:JSON.stringify({
      id:jarId, map_id:mapId, horizon:$('horizon').value.trim() || $('defHorizon').value.trim(), to:$('ns').value.trim()||'named'
    })});
    lastResolve = r; renderResolve(r); $('exportResolve').classList.remove('hide');
  }catch(e){err(e.message)}
  finally{busy($('runResolve'), false);}
};
$('exportResolve').onclick = () => download('fabrizon-resolve.json', lastResolve);

function renderResolve(rs){
  if(!rs.length){
    $('outResolve').innerHTML = '<div class="empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg><h3>Nothing to resolve</h3><p>Run analysis first, then click Resolve Names.</p></div>';
    return;
  }

  const counts = {};
  rs.forEach(x => counts[x.status] = (counts[x.status]||0)+1);

  let h = '<div class="results-summary">';
  for(const [k,v] of Object.entries(counts)){
    h += `<div class="summary-badge"><span class="count badge b-${k}">${v}</span><span class="label">${k}</span></div>`;
  }
  h += '</div>';

  h += rs.map(x => {
    const mixinShort = x.mixin.split('/').pop();
    return `<div class="card">
      <div class="row" style="align-items:flex-start; gap:12px; flex-wrap:wrap">
        <span class="badge b-${x.status}">${x.status}</span>
        <div style="flex:1; min-width:200px">
          <b class="mono">${esc(mixinShort)}</b>
          <span class="note">@${esc(x.annotation)} · ${esc(x.side)}</span>
        </div>
      </div>
      <div class="mono" style="margin-top:8px">${esc(x.java_target.split('/').pop())}#${esc(x.java_method)}${x.readable_target?' → '+esc(x.readable_target.split('/').pop())+'#'+esc(x.readable_method||''):''}</div>
      ${(x.candidates||[]).map((c,i)=>`<div class="cand">
        <div class="path">#${i+1} ${esc(c.path)} <span class="badge b-${x.status==='resolved'?'resolved':x.status}">${c.score} pts</span></div>
        <div class="meta">${esc(c.file)}:${c.line}</div>
        <div class="why">${esc(c.why.join('; '))}</div>
        ${c.target?`<div class="meta">Target ID: <code>${esc(c.target)}</code></div>`:''}
      </div>`).join('')}
      ${(x.notes||[]).map(n=>`<div class="note">• ${esc(n)}</div>`).join('')}
    </div>`;
  }).join('');

  $('outResolve').innerHTML = h;
}

/* ===== Step 3: Generate ===== */
$('runGenerate').onclick = async () => {
  if(!jarId){ toast('Upload a mod jar on Analyze tab first', 'warn'); return; }
  err(''); busy($('runGenerate'), true, 'Generating…');
  try{
    const r = await fetch('/api/generate', {
      method:'POST', headers:{'X-Token':T},
      body:JSON.stringify({
        id:jarId, map_id:mapId,
        horizon:$('horizon').value.trim() || $('defHorizon').value.trim(),
        to:$('ns').value.trim()||'named',
        crate:$('crate').value.trim() || $('defCrate').value.trim() || 'horizon_core',
        revision:$('rev').value.trim() || $('defMixinsRev').value.trim(),
        out:$('outDir').value.trim(),
        hnmod:$('hnmodPath').value.trim()||undefined,
        game:$('gameVer').value.trim() || $('defGame').value.trim() || '26.3',
        mixins_revision:$('mixinsRev').value.trim() || $('defMixinsRev').value.trim() || undefined,
        ai_key:$('genAiKey').value.trim() || $('settingsAiKey').value.trim() || undefined,
        ai_base:$('genAiBase').value.trim() || $('settingsAiBase').value.trim() || undefined,
        ai_model:$('genAiModel').value.trim() || $('settingsAiModel').value.trim() || undefined,
      })
    });
    if(!r.ok){
      let d={}; try{d=await r.json()}catch{}
      throw new Error(d.error || 'HTTP '+r.status);
    }
    const blob = await r.blob();
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download='fabrizon-bundle.zip'; a.click();
    toast('Bundle generated and downloaded as fabrizon-bundle.zip', 'ok');
  }catch(e){err(e.message)}
  finally{busy($('runGenerate'), false);}
};

/* ===== Init ===== */
document.addEventListener('DOMContentLoaded', () => {
  const v = new URLSearchParams(location.search).get('v');
  if(v) $('versionBadge').textContent = 'v'+v;
  loadSettings();
});
</script></body></html>
"""