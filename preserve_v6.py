from zipfile import ZipFile
from pathlib import Path
z=ZipFile('outputs/sifeng_planet_android_source.zip')
Path('outputs/PREVIOUS_VERSION.java').write_bytes(z.read('mobile/app/src/main/java/com/sifeng/planet/MainActivity.java'))
s=Path('work/SiFengPlanet.spec').read_text(encoding='utf-8')
s=s.replace("a.binaries = [entry for entry in a.binaries if entry[0].lower() not in ('icuuc.dll', 'icudt78.dll')]\n",'')
Path('outputs/PREVIOUS_SPEC.spec').write_text(s,encoding='utf-8')
z=ZipFile('outputs/sifeng_planet.zip')
Path('work/baseline-exe').mkdir(exist_ok=True)
Path('work/baseline-exe/SiFengPlanet.exe').write_bytes(z.read('SiFengPlanet.exe'))
print('PRESERVED: old_java old_spec old_exe')
