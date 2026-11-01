with open('src/fabrizon/gui_page.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Settings tab CSS before Responsive
old_css = """}
.toast.ok{border-left:4px solid var(--ok)}
.toast.err{border-left:4px solid var(--bad)}
.toast.warn{border-left:4px solid var(--warn)}
@keyframes slideIn{from{opacity:0; transform:translateX(20px)}to{opacity:1; transform:translateX(0)}}

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
<body><div class="wrap">"""

new_css = """}
.toast.ok{border-left:4px solid var(--ok)}
.toast.err{border-left:4px solid var(--bad)}
.toast.warn{border-left:4px solid var(--warn)}
@keyframes slideIn{from{opacity:0; transform:translateX(20px)}to{opacity:1; transform:translateX(0)}}

/* ===== Settings Tab ===== */
#t-settings{padding-top:8px}
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
.setting-actions{display:flex; gap:8px; margin-top:8px}
.status-indicator{display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border-radius:6px; font-size:12px; font-weight:600}
.status-indicator.ok{background:var(--ok-bg); color:var(--ok); border:1px solid rgba(56,217,169,.25)}
.status-indicator.warn{background:var(--warn-bg); color:var(--warn); border:1px solid rgba(255,195,90,.25)}
.status-indicator.err{background:var(--bad-bg); color:var(--bad); border:1px solid rgba(255,107,122,.25)}
.status-indicator .dot{width:8px; height:8px; border-radius:50%}
.status-indicator.ok .dot{background:var(--ok)}
.status-indicator.warn .dot{background:var(--warn)}
.status-indicator.err .dot{background:var(--bad)}

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
<body><div class="wrap">"""

if old_css in content:
    content = content.replace(old_css, new_css)
    print('CSS updated')
else:
    print('CSS old not found')

# 2. Add Settings tab to tabs
old_tabs = """<div class="tabs" role="tablist" aria-label="Pipeline steps">
    <div class="tab on" data-t="analyze" role="tab" aria-selected="true">1 \u00b7 Analyze</div>
    <div class="tab" data-t="resolve" role="tab" aria-selected="false">2 \u00b7 Resolve</div>
    <div class="tab" data-t="generate" role="tab" aria-selected="false">3 \u00b7 Generate</div>
  </div>"""

new_tabs = """<div class="tabs" role="tablist" aria-label="Pipeline steps">
    <div class="tab on" data-t="analyze" role="tab" aria-selected="true">1 \u00b7 Analyze</div>
    <div class="tab" data-t="resolve" role="tab" aria-selected="false">2 \u00b7 Resolve</div>
    <div class="tab" data-t="generate" role="tab" aria-selected="false">3 \u00b7 Generate</div>
    <div class="tab" data-t="settings" role="tab" aria-selected="false">\u2699 Settings</div>
  </div>"""

if old_tabs in content:
    content = content.replace(old_tabs, new_tabs)
    print('Tabs updated')
else:
    print('Tabs old not found')

# 3. Add Settings tab panel after Generate section
old_section = """<div id="outGenerate"></div>
  </section>
</div>"""

new_section = """<div id="outGenerate"></div>
  </section>

  <!-- Step 4: Settings -->
  <section id="t-settings" class="hide" role="tabpanel" aria-labelledby="tab-settings">
    <div class="settings-grid">
      <div class="setting-group">
        <h3>AI Translation</h3>
        <div class="setting-row">
          <label>API Key <span class="hint">NVIDIA / OpenAI-compatible key. Also set via <code>FABRIZON_NVIDIA_API_KEY</code> env var.</span></label>
          <input type="password" id="aiKey" placeholder="nvapi\u2026 or sk\u2026" autocomplete="off">
        </div>
        <div class="setting-row">
          <label>Base URL <span class="hint">Default: NVIDIA API.</span></label>
          <input type="text" id="aiBase" value="https://integrate.api.nvidia.com/v1">
        </div>
        <div class="setting-row">
          <label>Model <span class="hint">Default: Nemotron 3 Ultra.</span></label>
          <input type="text" id="aiModel" value="nvidia/nemotron-3-ultra-550b-a55b">
        </div>
        <div class="setting-actions">
          <button class="btn ghost" id="testAi">Test Connection</button>
          <span class="status-indicator hide" id="aiStatus"></span>
        </div>
      </div>
      <div class="setting-group">
        <h3>Defaults</h3>
        <div class="setting-row">
          <label>Horizon source folder <span class="hint">Path to your local Horizon checkout.</span></label>
          <input type="text" id="defHorizon" placeholder="C:\\path\\to\\horizon   or   /home/you/horizon">
        </div>
        <div class="setting-row">
          <label>Target namespace <span class="hint">Usually <code>named</code>.</span></label>
          <input type="text" id="defNs" value="named" style="max-width:240px">
        </div>
        <div class="setting-row">
          <label>Cargo target name <span class="hint">Prefix for target IDs, usually <code>horizon_core</code>.</span></label>
          <input type="text" id="defCrate" value="horizon_core" style="max-width:240px">
        </div>
        <div class="setting-row">
          <label>Minecraft version <span class="hint">For .hnmod manifest (e.g. <code>26.3</code>).</span></label>
          <input type="text" id="defGame" value="26.3" style="max-width:180px">
        </div>
        <div class="setting-row">
          <label>horizon-mixins revision <span class="hint">40-char commit for .hnmod.</span></label>
          <input type="text" id="defMixinsRev" placeholder="d9c83d7096b7ea5b83678da2efdfd6161f74997e" style="max-width:400px">
        </div>
      </div>
    </div>
  </section>
</div>"""

if old_section in content:
    content = content.replace(old_section, new_section)
    print('Settings section added')
else:
    print('Settings section old not found')

with open('src/fabrizon/gui_page.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('HTML updates done')