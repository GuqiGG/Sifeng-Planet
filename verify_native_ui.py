import importlib.util,os,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtMultimedia import QMediaPlayer
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QApplication([]);QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
w=m.MainWindow();a.aboutToQuit.connect(w.shutdown);w.cache_dir=Path('work/media-check').resolve()
w.items=[{'bvid':'BV1faak6AEzm','title':'司凤版 · 雨爱','author':'音乐收藏夹','duration':'02:19','pic':'','play':''}]
w.show();w.play_item(w.items[0]);w.audio.setVolume(0)
def done():
 assert w.windowFlags() & Qt.WindowType.FramelessWindowHint
 assert all(not b.icon().isNull() for b in [w.titlebar.min_button,w.titlebar.max_button,w.titlebar.close_button])
 assert w.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState
 assert w.player.position()>0 and w.player.duration()>0 and w.player.error()==QMediaPlayer.Error.NoError
 w.toggle_maximize();assert w.isMaximized()
 w.toggle_maximize();assert not w.isMaximized()
 w.repeat=True;w.ending_handled=False;w.on_media_status(QMediaPlayer.MediaStatus.EndOfMedia);assert not w.ending_handled
 called=[];w.next_video=lambda:called.append('next');w.repeat=False;w.ending_handled=False;w.on_media_status(QMediaPlayer.MediaStatus.EndOfMedia);assert called==['next']
 print('NATIVE_UI: frameless+SVG, MP4 PlayingState, repeat/next PASS',flush=True)
 a.quit()
QTimer.singleShot(4500,done);a.exec()
