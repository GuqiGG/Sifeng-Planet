import importlib.util, os, sys
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([])
original=m.MainWindow.load_settings
m.MainWindow.load_settings=lambda self:{'search_terms':list(m.KEYWORDS),'playback_mode':'continue','close_behavior':'tray','next_hotkey':'Ctrl+Alt+N','floating':False,'onboarding_complete':False}
w=m.MainWindow();m.MainWindow.load_settings=original
w.settings_path=__import__('pathlib').Path('work/motion-settings.json').resolve()
w.search=lambda:None;w.register_hotkey=lambda:None;w.show()
w.show_onboarding_preferences()
assert w.intro.start_button.size().width()==220 and w.intro.start_button.size().height()==58
assert w.pref_step==0 and w.pref_done.text()=='继续'
assert sum(control.isVisible() for _,control in w.pref_rows)==1
steps=[]
def advance():
    if len(steps)<4:
        w.advance_preferences();steps.append(1)
        QTimer.singleShot(550,advance)
    else:
        assert w.pref_step==4 and w.pref_done.text()=='开始听'
        assert sum(control.isVisible() for _,control in w.pref_rows)==1
        w.advance_preferences()
        assert not w.onboarding_mode and w.stack.currentIndex()==0
        w.show_favorites()
        assert w.stack.currentIndex()==4 and w.page_animation.state().name=='Running'
        print('MOTION: 5 guided steps; page transition running; start 220x58 PASS',flush=True)
        a.quit()
QTimer.singleShot(550,advance)
a.aboutToQuit.connect(w.shutdown)
a.exec()
