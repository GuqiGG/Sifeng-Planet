import importlib.util,os,sys
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QTimer
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([]);QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
old=m.MainWindow.load_settings
m.MainWindow.load_settings=lambda self:{'search_terms':list(m.KEYWORDS),'playback_mode':'continue','close_behavior':'tray','next_hotkey':'Ctrl+Alt+N','floating':False,'onboarding_complete':False}
w=m.MainWindow();m.MainWindow.load_settings=old;w.search=lambda:None;w.register_hotkey=lambda:None;w.show();a.aboutToQuit.connect(w.shutdown)
def capture_intro():
 w.grab().save('outputs/onboarding-preview.png')
 w.intro.exit_left()
 QTimer.singleShot(1100,capture_setup)
def capture_setup():
 w.grab().save('outputs/config-preview.png')
 print('INTRO_PREVIEW: title=%spt button=%dx%d step=%d visible_fields=%d PASS'%(w.intro.title.font().pointSizeF(),w.intro.start_button.width(),w.intro.start_button.height(),w.pref_step,sum(c.isVisible() for _,c in w.pref_rows)),flush=True)
 a.quit()
QTimer.singleShot(4800,capture_intro);a.exec()
