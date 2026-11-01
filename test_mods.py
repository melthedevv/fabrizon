import os, sys
sys.path.insert(0, 'src')
from fabrizon.jar import read_jar
from fabrizon.analysis import analyze

mods_dir = r'C:\Users\sesed\AppData\Roaming\PrismLauncher\instances\26.3\minecraft\mods'
test_mods = [
    'Clumps-fabric-26.3-26.3.2.jar',
    'MouseTweaks-fabric-mc26.3-2.31.jar',
    'letmedespawn-fabric-26.3-1.26.10.2.jar',
    'appleskin-fabric-mc26.3-3.0.10.jar',
    'krypton-0.3.2.jar',
    'modmenu-21.0.0.jar',
    'shulkerboxtooltip-fabric-5.4.3+26.3.jar',
    'lithium-fabric-0.26.3+mc26.3.jar',
    'iris-fabric-1.11.7+mc26.3.jar',
    'sodium-fabric-0.9.3-beta.1+mc26.3.jar',
    'ferritecore-9.0.0-fabric.jar',
    'zoomify-2.17.0+mc26.3-universal.jar',
]

for name in test_mods:
    path = os.path.join(mods_dir, name)
    if not os.path.exists(path):
        print(f'SKIP {name}: not found')
        continue
    try:
        jar = read_jar(path)
        rep = analyze(jar)
        m = rep.counts()
        print(f'{name}')
        print(f'  {rep.mod_id} {rep.version} | {rep.class_count} classes, {rep.mixin_class_count} mixins | mappable:{m.get("mappable",0)} review:{m.get("review",0)} blocked:{m.get("blocked",0)} | findings:{len(rep.findings)}')
    except Exception as e:
        print(f'ERROR {name}: {type(e).__name__}: {e}')