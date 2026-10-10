import importlib.util,sys
from PySide6.QtCore import QCoreApplication
spec=importlib.util.spec_from_file_location('app','outputs/sifeng_planet.pyw')
m=importlib.util.module_from_spec(spec);sys.modules['app']=m;spec.loader.exec_module(m)
a=QCoreApplication([])
assert m.search_keywords('雨爱',m.KEYWORDS)==('雨爱 司凤','雨爱 司凤版','雨爱 隆德齐')
assert m.search_keywords('雨爱',('自定义',))==('雨爱 司凤','雨爱 司凤版','雨爱 隆德齐')
found=[];errors=[]
w=m.SearchWorker(1,m.KEYWORDS,'雨爱')
w.batch.connect(lambda rows:found.extend(rows))
w.failed.connect(errors.append)
w.run()
assert not errors,errors
assert all(m.permitted(x['title']) for x in found)
print('LIVE_QUERY: keywords=3 results=%d allowed=%s PASS'%(len(found),bool(found)))
