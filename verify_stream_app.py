import importlib.util, json, os, sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtMultimedia import QMediaPlayer
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([]);w=m.MainWindow();a.aboutToQuit.connect(w.shutdown)
w.settings['onboarding_complete']=True;w.onboarding_mode=False;w.stack.setCurrentIndex(0)
w.library_path=Path('work/library-check/library.json').resolve();w.favorites=[];w.history=[]
w.cache_dir=Path('work/stream-app-cache').resolve();w.settings['floating']=True
w.search=lambda:None;w.register_hotkey=lambda:None
w.items=[{'bvid':'BV1faak6AEzm','title':'司凤版 · 雨爱','author':'音乐收藏夹','duration':'02:19','pic':'','play':''}]
w.show();w.audio.setVolume(0);w.play_item(w.items[0])
def done():
 assert w.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState,(w.status.text(),w.player.errorString())
 assert w.player.position()>0 and w.player.error()==QMediaPlayer.Error.NoError
 assert w.proxy is not None
 assert len(w.history)==1 and w.history[0]['bvid']=='BV1faak6AEzm'
 w.toggle_favorite(w.items[0]);assert len(w.favorites)==1
 assert json.loads(w.library_path.read_text(encoding='utf-8'))['favorites'][0]['bvid']=='BV1faak6AEzm'
 assert len(w.load_library()[0])==1 and len(w.load_library()[1])==1
 w.show_favorites();assert w.stack.currentIndex()==4
 w.show_history();assert w.stack.currentIndex()==5
 assert w.mini_capsule.isVisible() and w.mini_capsule.cover.timer.isActive() and w.mini_capsule.cover.angle>0
 complete=(w.cache_dir/'BV1faak6AEzm.mp4').exists()
 print('STREAM_APP: PlayingState pos=%d cache_complete=%s favorites=%d history=%d capsule=visible PASS' % (w.player.position(),complete,len(w.favorites),len(w.history)),flush=True)
 a.quit()
QTimer.singleShot(6000,done);a.exec()

