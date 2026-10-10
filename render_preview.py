import importlib.util,os,sys
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QTimer
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([]);QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
w=m.MainWindow();a.aboutToQuit.connect(w.shutdown);w.show()
def done():
 ok=w.grab().save('outputs/preview.png')
 print('PREVIEW: saved=%s items=%d all_allowed=%s' % (ok,len(w.items),all(m.permitted(x['title']) for x in w.items)),flush=True)
 a.quit()
QTimer.singleShot(18000,done);a.exec()
