import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
w=m.MediaWorker('BV1faak6AEzm',Path('work/media-check'),1)
result=[];errors=[]
w.ready.connect(lambda p: result.append(Path(p)))
w.failed.connect(lambda e: errors.append(e))
w.run()
assert not errors,errors
assert result and result[0].exists() and result[0].stat().st_size>10000
print('MEDIA_FETCH: Bilibili MP4 downloaded; bytes=%d; PASS' % result[0].stat().st_size)
