with open('src/fabrizon/gui_page.py', 'r') as f:
    content = f.read()

old = """/* ===== Mappings File ===== */
$('pickMap').onclick = () => $('mapFile').click();
$('mapFile').onchange = async e => {
  const f = e.target.files[0]; if(!f) return; err('');
  try{mapId = await upload(f, 'map'); $('mapName').textContent = f.name + ' (' + size(f.size) + ')'; $('mapName').classList.remove('note')}
  catch(x){err(x.message)}
};

/* ===== Clear Results ===== */"""

new = """/* ===== Mappings File ===== */
$('pickMap').onclick = () => $('mapFile').click();
$('mapFile').onchange = async e => {
  const f = e.target.files[0]; if(!f) return; err('');
  try{mapId = await upload(f, 'map'); $('mapName').textContent = f.name + ' (' + size(f.size) + ')'; $('mapName').classList.remove('note')}
  catch(x){err(x.message)}
};

/* ===== Settings ===== */
function loadSettings(){
  try{
    const s = JSON.parse(localStorage.getItem('fabrizon_settings') || '{}');
    if(s.aiKey) $('aiKey').value = s.aiKey;
    if(s.aiBase) $('aiBase').value = s.aiBase;
    if(s.aiModel) $('aiModel').value = s.aiModel;
    if(s.defHorizon) $('defHorizon').value = s.defHorizon;
    if(s.defNs) $('defNs').value = s.defNs;
    if(s.defCrate) $('defCrate').value = s.defCrate;
    if(s.defGame) $('defGame').value = s.defGame;
    if(s.defMixinsRev) $('defMixinsRev').value = s.defMixinsRev;
  }catch{}
}
function saveSettings(){
  const s = {
    aiKey: $('aiKey').value,
    aiBase: $('aiBase').value,
    aiModel: $('aiModel').value,
    defHorizon: $('defHorizon').value,
    defNs: $('defNs').value,
    defCrate: $('defCrate').value,
    defGame: $('defGame').value,
    defMixinsRev: $('defMixinsRev').value,
  };
  localStorage.setItem('fabrizon_settings', JSON.stringify(s));
  return s;
}
function applySettingsToGenerateForm(s){
  if(s.aiKey) $('aiKey').value = s.aiKey;
  if(s.defHorizon) $('horizon').value = s.defHorizon;
  if(s.defNs) $('ns').value = s.defNs;
  if(s.defCrate) $('crate').value = s.defCrate;
  if(s.defGame) $('gameVer').value = s.defGame;
  if(s.defMixinsRev) $('mixinsRev').value = s.defMixinsRev;
}
async function testAiConnection(){
  const btn = $('testAi');
  const status = $('aiStatus');
  const key = $('aiKey').value.trim();
  const base = $('aiBase').value.trim() || 'https://integrate.api.nvidia.com/v1';
  const model = $('aiModel').value.trim() || 'nvidia/nemotron-3-ultra-550b-a55b';
  if(!key){ status.textContent='Enter API key first'; status.className='status-indicator warn'; status.classList.remove('hide'); return; }
  busy(btn, true, 'Testing…');
  status.classList.add('hide');
  try{
    const r = await fetch(base + '/models', {headers:{'Authorization':'Bearer '+key}});
    if(r.ok){
      status.textContent='Connected OK'; status.className='status-indicator ok'; status.classList.remove('hide');
      toast('API connection successful', 'ok');
    }else{
      const t = await r.text();
      status.textContent='Failed: '+r.status; status.className='status-indicator err'; status.classList.remove('hide');
      toast('API test failed: '+r.status, 'err');
    }
  }catch(e){
    status.textContent='Error: '+e.message; status.className='status-indicator err'; status.classList.remove('hide');
    toast('API test error: '+e.message, 'err');
  }
  finally{busy(btn, false);}
}
$('testAi').onclick = testAiConnection;
['aiKey','aiBase','aiModel','defHorizon','defNs','defCrate','defGame','defMixinsRev'].forEach(id=>{
  const el = $(id); if(el) el.onchange = () => saveSettings();
});
loadSettings();
applySettingsToGenerateForm(JSON.parse(localStorage.getItem('fabrizon_settings') || '{}'));

/* ===== Clear Results ===== */"""

if old in content:
    content = content.replace(old, new)
    with open('src/fabrizon/gui_page.py', 'w') as f:
        f.write(content)
    print('SUCCESS: Settings JS added')
else:
    print('OLD NOT FOUND')
    idx = content.find("/* ===== Mappings File ===== */")
    if idx >= 0:
        print('Found at', idx)
        print(repr(content[idx:idx+300]))
    else:
        print('Mappings File section not found')