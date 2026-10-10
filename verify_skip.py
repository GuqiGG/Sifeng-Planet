import importlib.util, os, sys, json
from pathlib import Path
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
spec = importlib.util.spec_from_file_location('app', 'outputs/sifeng_planet.pyw')
m = importlib.util.module_from_spec(spec); sys.modules['app'] = m; spec.loader.exec_module(m)
a = QApplication([])
original = m.MainWindow.load_settings
m.MainWindow.load_settings = lambda self: {'search_terms': list(m.KEYWORDS), 'playback_mode': 'continue', 'close_behavior': 'tray', 'next_hotkey': 'Ctrl+Alt+N', 'floating': False, 'onboarding_complete': False}
w = m.MainWindow(); m.MainWindow.load_settings = original
w.settings_path = Path('work/skip-settings.json').resolve()
w.search = lambda: None; w.register_hotkey = lambda: None
assert w.onboarding_mode
w.skip_onboarding()
assert not w.onboarding_mode and w.stack.currentIndex() == 0
assert json.loads(w.settings_path.read_text(encoding='utf-8'))['onboarding_complete']
print('SKIP: first-run defaults saved; home opened PASS')
w.shutdown(); a.quit()
