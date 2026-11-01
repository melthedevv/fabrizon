"""The single-page UI served by `fabrizon gui`. No external assets, works offline."""

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fabrizon</title>
<style>
:root{--bg:#0e1015;--panel:#161922;--panel2:#1c2030;--line:#2a2f42;--text:#e7e9f2;--mute:#8b91a8;
--accent:#7c8cff;--accent2:#b07cff;--ok:#3ecf8e;--warn:#f5b748;--bad:#ff6b6b}
@media (prefers-color-scheme:light){:root{--bg:#f5f6fb;--panel:#fff;--panel2:#eef0f8;--line:#d9dcea;--text:#1a1d2b;--mute:#667;--accent:#5566e8;--accent2:#8a55e8}}
*{box-sizing:border-box}html,body{margin:0}
body{background:var(--bg);color:var(--text);font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:28px 20px 60px}
header{display:flex;align-items:center;gap:14px;margin-bottom:22px}
.logo{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:grid;place-items:center;font-weight:800;font-size:22px;color:#fff}
h1{margin:0;font-size:22px;letter-spacing:.2px}.sub{color:var(--mute);font-size:13px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:16px}
.drop{border:2px dashed var(--line);border-radius:14px;padding:34px;text-align:center;cursor:pointer;transition:.15s;background:var(--panel)}
.drop:hover,.drop.over{border-color:var(--accent);background:var(--panel2)}
.drop b{display:block;font-size:16px;margin-bottom:4px}.drop span{color:var(--mute)}
.tabs{display:flex;gap:6px;margin:0 0 16px}
.tab{padding:8px 16px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--mute);cursor:pointer;font-weight:600}
.tab.on{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border-color:transparent}
button.btn{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border:0;border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-size:14px}
button.btn:disabled{opacity:.45;cursor:not-allowed}button.ghost{background:var(--panel2);color:var(--text);border:1px solid var(--line)}
input[type=text]{width:100%;background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:10px 12px;color:var(--text);font:inherit}
label{display:block;font-weight:600;margin:12px 0 5px}.hint{color:var(--mute);font-size:12px;font-weight:400}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.stat{background:var(--panel2);border-radius:12px;padding:12px 14px}.stat .n{font-size:26px;font-weight:800}.stat .l{color:var(--mute);font-size:12px}
.n.ok{color:var(--ok)}.n.warn{color:var(--warn)}.n.bad{color:var(--bad)}
.kv{display:grid;grid-template-columns:130px 1fr;gap:6px 12px}.kv div:nth-child(odd){color:var(--mute)}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 12px}
.chip{padding:5px 12px;border-radius:99px;border:1px solid var(--line);cursor:pointer;color:var(--mute);background:var(--panel2);font-weight:600;font-size:12px}
.chip.on{color:#fff;background:var(--accent);border-color:transparent}
table{width:100%;border-collapse:collapse}th{text-align:left;color:var(--mute);font-weight:600;font-size:12px;padding:6px 8px}
td{padding:9px 8px;border-top:1px solid var(--line);vertical-align:top}code,.mono{font-family:ui-monospace,Consolas,monospace;font-size:12.5px;word-break:break-all}
.badge{display:inline-block;padding:2px 9px;border-radius:99px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}
.b-mappable,.b-resolved{background:#3ecf8e22;color:var(--ok)}.b-review,.b-ambiguous,.b-needs-mappings{background:#f5b74822;color:var(--warn)}
.b-blocked,.b-unresolved{background:#ff6b6b22;color:var(--bad)}
.note{color:var(--mute);font-size:12.5px}.cand{margin:4px 0 0;padding:6px 10px;background:var(--panel2);border-radius:8px}
.err{background:#ff6b6b1f;border:1px solid var(--bad);color:var(--bad);padding:10px 14px;border-radius:10px;margin-bottom:14px;white-space:pre-wrap}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.sp{flex:1}.hide{display:none}
footer{margin-top:26px;color:var(--mute);font-size:12px;text-align:center}footer a{color:var(--accent)}
.spin{display:inline-block;width:14px;height:14px;border:2px solid #fff6;border-top-color:#fff;border-radius:50%;animation:s .7s linear infinite;vertical-align:-2px;margin-right:6px}
@keyframes s{to{transform:rotate(360deg)}}
</style></head><body><div class="wrap">
<header><div class="logo">F</div><div><h1>Fabrizon</h1><div class="sub">Translate Fabric mods for Horizon &middot; unofficial</div></div></header>
<div id="err" class="err hide"></div>

<div id="drop" class="drop"><b>Drop a Fabric mod .jar here</b><span>or click to choose one &middot; files stay on this computer</span>
<input id="file" type="file" accept=".jar,.zip" class="hide"></div>
<div id="loaded" class="card hide"><div class="row"><div><b id="fname"></b><div class="note" id="fsize"></div></div><div class="sp"></div>
<button class="btn ghost" id="swap">Choose another</button></div></div>

<div id="main" class="hide">
<div class="tabs"><div class="tab on" data-t="analyze">1 &middot; Analyze</div><div class="tab" data-t="resolve">2 &middot; Resolve names</div></div>

<section id="t-analyze"><div class="row" style="margin-bottom:14px"><button class="btn" id="runA">Run analysis</button><div class="sp"></div>
<button class="btn ghost hide" id="expA">Export JSON</button></div><div id="outA"></div></section>

<section id="t-resolve" class="hide"><div class="card">
<label>Mappings file <span class="hint">Tiny v1/v2 (intermediary or Yarn), .tiny or .gz. Needed when the jar uses class_1234 style names.</span></label>
<div class="row"><button class="btn ghost" id="pickMap">Choose mappings…</button><span class="note" id="mapName">none</span><input id="mapFile" type="file" class="hide"></div>
<label>Horizon source folder <span class="hint">Path to your local Horizon checkout on this computer.</span></label>
<input type="text" id="horizon" placeholder="C:\path\to\horizon   or   /home/you/horizon">
<label>Target namespace <span class="hint">Usually "named".</span></label><input type="text" id="ns" value="named" style="max-width:220px">
<label>Cargo target name <span class="hint">Prefix for target IDs, usually horizon_core.</span></label><input type="text" id="crate" value="horizon_core" style="max-width:220px">
<label>Horizon commit <span class="hint">Optional exact 40-character hash for [compatibility].</span></label><input type="text" id="rev" placeholder="028f6088...">
<div class="row" style="margin-top:16px"><button class="btn" id="runR">Resolve</button><button class="btn ghost" id="runG">Generate bundle (.zip)</button><div class="sp"></div><button class="btn ghost hide" id="expR">Export JSON</button></div></div>
<div id="outR"></div></section>
</div>

<footer>Made by <b>melthedev</b> &middot; <a href="https://ko-fi.com/melthedev" target="_blank" rel="noopener">Support on Ko-fi</a><br>
Not affiliated with the Horizon project, Mojang or Microsoft. Results are candidates: run <code>horizon-mixins plan</code> and <code>check</code> on the pinned Horizon source before trusting a bundle.</footer>
</div>
<script>
const T=new URLSearchParams(location.search).get('t')||'';
const $=id=>document.getElementById(id);
let jarId=null,mapId=null,lastA=null,lastR=null;
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function err(m){const e=$('err');e.textContent=m||'';e.classList.toggle('hide',!m)}
async function api(path,opts={}){
  const r=await fetch(path,{...opts,headers:{'X-Token':T,...(opts.headers||{})}});
  let d;try{d=await r.json()}catch{d={error:'Bad response from server'}}
  if(!r.ok||d.error)throw new Error(d.error||('HTTP '+r.status));return d}
async function upload(file,kind){
  const d=await api('/api/upload?kind='+kind+'&name='+encodeURIComponent(file.name),{method:'POST',body:file});return d.id}
function size(n){return n>1048576?(n/1048576).toFixed(1)+' MB':Math.max(1,Math.round(n/1024))+' KB'}
async function takeJar(f){
  if(!f)return;err('');
  try{jarId=await upload(f,'jar')}catch(e){err(e.message);return}
  $('fname').textContent=f.name;$('fsize').textContent=size(f.size);
  $('drop').classList.add('hide');$('loaded').classList.remove('hide');$('main').classList.remove('hide');
  $('outA').innerHTML='';$('outR').innerHTML='';lastA=lastR=null;$('expA').classList.add('hide');$('expR').classList.add('hide');
  runAnalyze()}
const drop=$('drop');drop.onclick=()=>$('file').click();$('swap').onclick=()=>$('file').click();
$('file').onchange=e=>takeJar(e.target.files[0]);
['dragover','dragenter'].forEach(ev=>document.addEventListener(ev,e=>{e.preventDefault();drop.classList.add('over')}));
['dragleave','drop'].forEach(ev=>document.addEventListener(ev,e=>{e.preventDefault();drop.classList.remove('over')}));
document.addEventListener('drop',e=>{const f=e.dataTransfer.files[0];if(f)takeJar(f)});
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x===t));
  $('t-analyze').classList.toggle('hide',t.dataset.t!=='analyze');$('t-resolve').classList.toggle('hide',t.dataset.t!=='resolve')});
$('pickMap').onclick=()=>$('mapFile').click();
$('mapFile').onchange=async e=>{const f=e.target.files[0];if(!f)return;err('');
  try{mapId=await upload(f,'map');$('mapName').textContent=f.name+' ('+size(f.size)+')'}catch(x){err(x.message)}};
function busy(b,on,txt){b.disabled=on;if(on){b.dataset.t=b.textContent;b.innerHTML='<span class="spin"></span>'+txt}else b.textContent=b.dataset.t||b.textContent}
function download(name,obj){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(obj,null,2)],{type:'application/json'}));a.download=name;a.click()}
$('expA').onclick=()=>download('fabrizon-analysis.json',lastA);$('expR').onclick=()=>download('fabrizon-resolve.json',lastR);

async function runAnalyze(){
  err('');busy($('runA'),true,'Analyzing…');
  try{const r=await api('/api/analyze',{method:'POST',body:JSON.stringify({id:jarId})});lastA=r;renderA(r);$('expA').classList.remove('hide')}
  catch(e){err(e.message)}finally{busy($('runA'),false)}}
$('runA').onclick=runAnalyze;
let filt='all';
function renderA(r){
  const c=r.counts,f=r.findings;
  let h=`<div class="card"><div class="kv"><div>Mod</div><div><b>${esc(r.mod_id)}</b> ${esc(r.version)}</div>
  <div>License</div><div>${esc(typeof r.license==='object'?JSON.stringify(r.license):r.license||'not declared')}</div>
  <div>Authors</div><div>${esc((r.authors||[]).join(', ')||'unknown')}</div>
  <div>Classes</div><div>${r.class_count} (${r.mixin_class_count} mixin classes)</div>
  <div>Sides</div><div>common ${r.sides.common} &middot; client ${r.sides.client} &middot; server ${r.sides.server}</div>
  <div>Content files</div><div>${r.asset_files} assets, ${r.data_files} data files</div>
  <div>Names</div><div>${r.intermediary_names?'<span class="badge b-review">intermediary</span> needs mappings in step 2':'readable'}</div></div></div>
  <div class="grid" style="margin-bottom:16px"><div class="stat"><div class="n ok">${c.mappable}</div><div class="l">Mappable</div></div>
  <div class="stat"><div class="n warn">${c.review}</div><div class="l">Needs review</div></div>
  <div class="stat"><div class="n bad">${c.blocked}</div><div class="l">Blocked</div></div></div>`;
  (r.warnings||[]).forEach(w=>h+=`<div class="err" style="color:var(--warn);border-color:var(--warn);background:#f5b7481f">${esc(w)}</div>`);
  h+=`<div class="card"><b>Injection points</b><div class="chips">`+['all','mappable','review','blocked'].map(k=>`<span class="chip ${filt===k?'on':''}" data-f="${k}">${k}</span>`).join('')+`</div>`;
  const rows=f.filter(x=>filt==='all'||x.status===filt);
  h+=rows.length?`<table><tr><th>Status</th><th>Mixin / member</th><th>Target</th><th>Horizon kind</th></tr>`+rows.map(x=>`<tr><td><span class="badge b-${x.status}">${x.status}</span></td>
  <td class="mono">${esc(x.mixin.split('/').pop())}<br><span class="note">${esc(x.member)} &middot; ${esc(x.annotation)} &middot; ${esc(x.side)}</span></td>
  <td class="mono">${esc((x.targets||[]).map(t=>t.split('/').pop()).join(', '))}<br><span class="note">${esc((x.selectors||[]).join(', '))}</span></td>
  <td>${esc(x.horizon||'-')}<div class="note">${esc(x.note)}</div></td></tr>`).join('')+`</table>`:`<div class="note">Nothing here.</div>`;
  h+=`</div>`;
  if((r.fabric_api_refs||[]).length)h+=`<div class="card"><b>Fabric API used</b> <span class="hint">(not mixins, needs an event-to-site table)</span><div class="mono" style="margin-top:8px">${r.fabric_api_refs.map(esc).join('<br>')}</div></div>`;
  $('outA').innerHTML=h;
  $('outA').querySelectorAll('.chip').forEach(ch=>ch.onclick=()=>{filt=ch.dataset.f;renderA(r)})}

$('runR').onclick=async()=>{
  err('');busy($('runR'),true,'Resolving…');
  try{const r=await api('/api/resolve',{method:'POST',body:JSON.stringify({id:jarId,map_id:mapId,horizon:$('horizon').value.trim(),to:$('ns').value.trim()||'named'})});
    lastR=r;renderR(r);$('expR').classList.remove('hide')}catch(e){err(e.message)}finally{busy($('runR'),false)}};
$('runG').onclick=async()=>{
  err('');busy($('runG'),true,'Generating…');
  try{const r=await fetch('/api/generate',{method:'POST',headers:{'X-Token':T},body:JSON.stringify({id:jarId,map_id:mapId,horizon:$('horizon').value.trim(),to:$('ns').value.trim()||'named',crate:$('crate').value.trim(),revision:$('rev').value.trim()})});
    if(!r.ok){let d={};try{d=await r.json()}catch{}throw new Error(d.error||('HTTP '+r.status))}
    const a=document.createElement('a');a.href=URL.createObjectURL(await r.blob());a.download='fabrizon-bundle.zip';a.click()}
  catch(e){err(e.message)}finally{busy($('runG'),false)}};
function renderR(rs){
  if(!rs.length){$('outR').innerHTML='<div class="card note">Nothing to resolve.</div>';return}
  const t={};rs.forEach(x=>t[x.status]=(t[x.status]||0)+1);
  let h='<div class="chips">'+Object.entries(t).map(([k,v])=>`<span class="badge b-${k}">${k} ${v}</span>`).join(' ')+'</div>';
  h+=rs.map(x=>`<div class="card"><div class="row"><span class="badge b-${x.status}">${x.status}</span><b class="mono">${esc(x.mixin.split('/').pop())}</b><span class="note">@${esc(x.annotation)}</span></div>
  <div class="mono" style="margin-top:6px">${esc(x.java_target.split('/').pop())}#${esc(x.java_method)}${x.readable_target?` &rarr; ${esc(x.readable_target.split('/').pop())}#${esc(x.readable_method||'')}`:''}</div>
  ${(x.candidates||[]).map(c=>`<div class="cand"><div class="mono"><b>${esc(c.path)}</b> <span class="note">score ${c.score}</span></div><div class="note">${esc(c.file)}:${c.line} &middot; ${esc(c.why.join('; '))}</div></div>`).join('')}
  ${(x.notes||[]).map(n=>`<div class="note">&bull; ${esc(n)}</div>`).join('')}</div>`).join('');
  $('outR').innerHTML=h}
</script></body></html>
"""
