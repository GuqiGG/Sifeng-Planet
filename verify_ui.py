import importlib.util, json, os, sys
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QTWEBENGINE_DISABLE_SANDBOX']='1'
from pathlib import Path
from PySide6.QtWidgets import QApplication
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([]);w=m.MainWindow();a.aboutToQuit.connect(w.shutdown)
w.settings_path=Path('work/test-settings.json')
w.save_repeat(True)
assert json.loads(w.settings_path.read_text(encoding='utf-8'))['repeat'] is True
w.items=[{'bvid':'BV1abc','title':'司凤版 一','author':'A','duration':'1:00'}, {'bvid':'BV2abc','title':'隆德齐 二','author':'B','duration':'2:00'}]
played=[];w.play_item=lambda item: played.append(item['bvid'])
w.index=0;w.repeat=False;w.ending_handled=False;w.on_video_end_check(True)
assert w.index==1 and played==['BV2abc']
class FakeWeb:
 def page(self): return self
 def runJavaScript(self,script,callback): callback(True)
w.web=FakeWeb();w.repeat=True;w.ending_handled=False;w.on_video_end_check(True)
assert w.index==1 and w.ending_handled is False
print('UI LOGIC: settings persisted; next video BV2abc; repeat current PASS')
a.quit()
