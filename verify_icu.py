import pathlib, struct, subprocess, sys
import pefile
qt=pefile.PE('D:/Apps/Python/Lib/site-packages/PySide6/Qt6Core.dll')
need={x.name.decode() for e in qt.DIRECTORY_ENTRY_IMPORT if e.dll.lower()==b'icuuc.dll' for x in e.imports if x.name}
wrong=pefile.PE('C:/Users/guqig/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/icuuc.dll')
has={x.name.decode(errors='ignore') for x in wrong.DIRECTORY_ENTRY_EXPORT.symbols if x.name}
def entries(path):
 result=subprocess.run([sys.executable,'-m','PyInstaller.utils.cliutils.archive_viewer','-b',str(path)],capture_output=True,text=True,check=True)
 return result.stdout.splitlines()
old=pathlib.Path('work/baseline-exe/SiFengPlanet.exe')
new=pathlib.Path('outputs/SiFengPlanet.exe')
old_bad=any(x.strip()=='icuuc.dll' for x in entries(old))
new_bad=any(x.strip()=='icuuc.dll' for x in entries(new))
raw=new.read_bytes(); pe=struct.unpack_from('<I',raw,0x3c)[0]; subsystem=struct.unpack_from('<H',raw,pe+24+68)[0]
assert old_bad and not new_bad and len(need-has)==20 and subsystem==2
if len(sys.argv) < 2 or sys.argv[1] == '--baseline':
 print('BASELINE_ICU: bundled_conflict=True missing_exports=20 PASS')
if len(sys.argv) < 2 or sys.argv[1] == '--modified':
 print('MODIFIED_ICU: bundled_conflict=False gui_subsystem=2 PASS')
