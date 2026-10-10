import importlib.util, os, sys
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QTWEBENGINE_DISABLE_SANDBOX']='1'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([]);w=m.MainWindow();a.aboutToQuit.connect(w.shutdown);w.show()
def done():
 print('UI SEARCH: count=%d all_allowed=%s status=%s' % (len(w.items),all(m.permitted(x['title']) for x in w.items),w.status.text()),flush=True)
 a.quit()
QTimer.singleShot(18000,done);a.exec()
