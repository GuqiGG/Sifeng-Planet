import importlib.util,os,sys
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([])
old=m.MainWindow.load_settings
m.MainWindow.load_settings=lambda self:{'search_terms':list(m.KEYWORDS),'playback_mode':'continue','close_behavior':'tray','next_hotkey':'Ctrl+Alt+N','floating':False,'onboarding_complete':True}
w=m.MainWindow();m.MainWindow.load_settings=old
w.settings_path=Path('work/query-settings.json').resolve();w.register_hotkey=lambda:None;w.show()
w.query.setText('雨爱');w.submit_query()
def done():
 if w.worker and w.worker.isRunning():QTimer.singleShot(100,done);return
 assert w.active_query=='雨爱' and len(w.items)>0 and all(m.permitted(x['title']) for x in w.items)
 old_page=w.page;w.search=lambda:None;w.refresh()
 assert w.page!=old_page and 1<=w.page<=5 and len(w.items)==0
 print('QUERY_UI: remote_results=%d refresh_page=%d previous_page=%d PASS'%(len(w.items_before),w.page,old_page),flush=True)
 a.quit()
def checked():
 if w.worker and w.worker.isRunning():QTimer.singleShot(100,checked);return
 w.items_before=list(w.items);done()
QTimer.singleShot(100,checked);a.aboutToQuit.connect(w.shutdown);a.exec()
