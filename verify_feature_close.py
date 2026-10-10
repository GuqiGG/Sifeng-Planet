import importlib.util,os,sys
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([]);QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
old=m.MainWindow.load_settings
m.MainWindow.load_settings=lambda self:{'search_terms':list(m.KEYWORDS),'playback_mode':'continue','close_behavior':'tray','next_hotkey':'Ctrl+Alt+N','floating':False,'onboarding_complete':False}
w=m.MainWindow();m.MainWindow.load_settings=old
w.onboarding_mode=False;w.stack.setCurrentIndex(0);w.set_onboarding_chrome(False);w.status.show();w.show()
w.items=[{'bvid':'BV1faak6AEzm','title':'雨爱（司凤版）','author':'音乐收藏夹','duration':'2:20','pic':'','play':''}]
w.render_cards()
assert w.featured.isVisible() and w.feature_close.isVisible()
prior=w.player.playbackState()
w.dismiss_feature()
assert w.feature_dismissed and not w.featured.isVisible()
assert w.player.playbackState()==prior
assert w.feature_animation.state().name=='Running'
def done():
 assert w.last_dismiss_tip.isVisible()
 assert '正在播放' in w.last_dismiss_tip.text()
 w.grab().save('outputs/feature-closed-preview.png')
 print('FEATURE_CLOSE: slides_to=player_nav hint=visible playback_unchanged=True PASS',flush=True)
 a.quit()
QTimer.singleShot(800,done);a.aboutToQuit.connect(w.shutdown);a.exec()
