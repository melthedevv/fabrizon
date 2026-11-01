import os, sys, tempfile, shutil
sys.path.insert(0, 'src')
from fabrizon.jar import read_jar
from fabrizon.analysis import analyze
from fabrizon.mappings import load_tiny
from fabrizon.rustindex import index_tree
from fabrizon.resolve import resolve
from fabrizon.generate import generate, write_bundle
from fabrizon.package import package_bundle, build_compatibility

mods_dir = r'C:\Users\sesed\AppData\Roaming\PrismLauncher\instances\26.3\minecraft\mods'

# Index Horizon once
print("Indexing Horizon...")
HZ = r'C:\Users\sesed\AppData\Local\Temp\opencode\hz\hzsrc\horizon-ba6344a59cb9e755b730dcf02285fc0d33b97d3c'
fns = index_tree(HZ)
print(f'  Indexed {len(fns)} functions')

maps = load_tiny(r'C:\Users\sesed\AppData\Local\Temp\opencode\hz\yarn.tiny')

test_mods = [
    'appleskin-fabric-mc26.3-3.0.10.jar',      # 9 mappable
    'shulkerboxtooltip-fabric-5.4.3+26.3.jar',  # 10 mappable
    'ferritecore-9.0.0-fabric.jar',            # 3 mappable
    'zoomify-2.17.0+mc26.3-universal.jar',     # 0 mappable but has RETURN
]

for name in test_mods:
    path = os.path.join(mods_dir, name)
    print(f'\n=== {name} ===')
    try:
        jar = read_jar(path)
        rep = analyze(jar)
        print(f'  Analyze: {rep.mod_id} {rep.version} | {len(rep.findings)} findings')
        
        rs = resolve(rep, fns, maps)
        resolved = [r for r in rs if r.status == 'resolved']
        print(f'  Resolve: {len(resolved)}/{len(rs)} resolved')
        for r in resolved:
            c = r.candidates[0]
            print(f'    {r.kind or "?":6} {r.member:30} -> {c.target}')
        
        if not resolved:
            print('  SKIP generate: no resolved targets')
            continue
            
        # Generate
        tmpdir = tempfile.mkdtemp(prefix=f'fabrizon_{rep.mod_id}_')
        b = generate(rep, rs, 'horizon_core', 'ba6344a59cb9e755b730dcf02285fc0d33b97d3c', jar)
        paths = write_bundle(b, tmpdir)
        print(f'  Generate: {len(paths)} files, {len(b.emitted)} injections')
        
        if not b.emitted:
            print('  SKIP package: no live injections (only HEAD/RETURN generate bundles)')
            shutil.rmtree(tmpdir, ignore_errors=True)
            continue
        
        # Package
        compat = build_compatibility(
            HZ, game='26.3',
            horizon_revision='ba6344a59cb9e755b730dcf02285fc0d33b97d3c',
            mixins_revision='d9c83d7096b7ea5b83678da2efdfd6161f74997e',
        )
        hnmod = os.path.join(tmpdir, f'{rep.mod_id}.hnmod')
        packed = package_bundle(tmpdir, hnmod, compat)
        print(f'  Package: {packed.size} bytes, sha256 {packed.sha256[:16]}...')
        
        shutil.rmtree(tmpdir, ignore_errors=True)
        
    except Exception as e:
        print(f'  ERROR: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()

print('\n=== ALL DONE ===')