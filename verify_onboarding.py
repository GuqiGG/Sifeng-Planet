import ctypes, importlib.util, json, os, sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase,QKeySequence
from PySide6.QtCore import QTimer
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([]);QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
original_load=m.MainWindow.load_settings
m.MainWindow.load_settings=lambda self: {'search_terms':list(m.KEYWORDS),'playback_mode':'continue','close_behavior':'tray','next_hotkey':'Ctrl+Alt+N','floating':False,'onboarding_complete':False}
w=m.MainWindow();m.MainWindow.load_settings=original_load
a.aboutToQuit.connect(w.shutdown);w.settings_path=Path('work/onboarding-settings.json');w.search=lambda:None;w.register_hotkey=lambda:None;w.show()
assert w.onboarding_mode and w.stack.currentIndex()==3
w.terms_edit.setText('司凤、测试歌曲')
w.mode_combo.setCurrentIndex(w.mode_combo.findData('random'))
w.exit_combo.setCurrentIndex(w.exit_combo.findData('quit'))
w.hotkey_edit.setKeySequence(QKeySequence('Ctrl+Alt+M'))
w.float_box.setChecked(True)
assert m.hotkey_parts(w.hotkey_edit.keySequence())==(0x4003,77)
w.apply_preferences()
assert not w.onboarding_mode and w.stack.currentIndex()==0
saved=json.loads(w.settings_path.read_text(encoding='utf-8'))
assert saved['search_terms']==['司凤','测试歌曲'] and saved['playback_mode']=='random'
assert saved['close_behavior']=='quit' and saved['next_hotkey']=='Ctrl+Alt+M'
assert saved['floating'] and saved['onboarding_complete']
assert not m.permitted('隆德齐歌曲',saved['search_terms']) and m.permitted('测试歌曲 新作',saved['search_terms'])
assert w.load_settings()['onboarding_complete']
# Native WM_HOTKEY dispatches the next-song action even while the main view is hidden.
called=[];w.next_video=lambda:called.append('next')
msg=m.wintypes.MSG();msg.message=0x0312;msg.wParam=0x5346
assert w.nativeEvent('windows_generic_MSG',ctypes.addressof(msg))==(True,0)
def done():
 assert called==['next']
 print('ONBOARDING: saved terms/random/quit/hotkey/capsule; first-run only; WM_HOTKEY PASS',flush=True)
 a.quit()
QTimer.singleShot(100,done);a.exec()

