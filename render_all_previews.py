import importlib.util,os,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QTimer
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([]);QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
w=m.MainWindow();a.aboutToQuit.connect(w.shutdown)
w.onboarding_mode=False;w.settings['search_terms']=list(m.KEYWORDS);w.stack.setCurrentIndex(0);w.set_onboarding_chrome(False);w.status.show()
w.library_path=Path('work/preview-library/library.json').resolve();w.favorites=[];w.history=[]
w.show()
if not w.worker or not w.worker.isRunning():w.search()
def finish(item):
 w.grab().save('outputs/favorites-preview.png')
 w.mini_capsule.set_track(item);w.mini_capsule.show();w.mini_capsule.set_playing(True)
 w.mini_capsule.grab().save('outputs/capsule-preview.png')
 print('PREVIEWS: items=%d favorite=%d all_allowed=%s' % (len(w.items),len(w.favorites),all(m.permitted(x['title']) for x in w.items)),flush=True)
 a.quit()
def done():
 w.grab().save('outputs/preview.png')
 if w.items:
  item=w.items[0]
  w.toggle_favorite(item);w.show_favorites()
  QTimer.singleShot(300,lambda:finish(item))
 else:
  print('PREVIEWS: no items',flush=True);a.quit()
QTimer.singleShot(18000,done);a.exec()

