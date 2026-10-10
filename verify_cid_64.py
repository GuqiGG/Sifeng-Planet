import ctypes
import pathlib
import requests
import sys

mode = sys.argv[1]
old = pathlib.Path('outputs/PREVIOUS_VERSION.java').read_text(encoding='utf-8')
new = pathlib.Path('mobile/app/src/main/java/com/sifeng/planet/MainActivity.java').read_text(encoding='utf-8')
assert 'int cid;' in old and '.getInt("cid")' in old
assert 'long aid=song.optLong("aid"),cid;' in new and '.getInt("cid")' not in new

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com/',
})
session.get('https://www.bilibili.com/', timeout=15).raise_for_status()
bvid = 'BV1faak6AEzm'
pages = session.get('https://api.bilibili.com/x/player/pagelist', params={'bvid': bvid}, timeout=15).json()
cid = pages['data'][0]['cid']
assert cid > 2**31 - 1
if mode == '--baseline':
    response = session.get('https://api.bilibili.com/x/player/playurl', params={
        'bvid': bvid, 'cid': ctypes.c_int(cid).value, 'qn': 16, 'fnval': 0,
    }, timeout=15).json()
    assert response['code'] == -400
    print(f'BASELINE_CID: cid={cid} int32={ctypes.c_int(cid).value} api_code=-400 PASS')
elif mode == '--modified':
    response = session.get('https://api.bilibili.com/x/player/playurl', params={
        'bvid': bvid, 'cid': cid, 'qn': 16, 'fnval': 0,
    }, timeout=15).json()
    assert response['code'] == 0 and response['data']['durl'][0]['url']
    print(f'MODIFIED_CID: cid={cid} int64_preserved=True api_code=0 mp4=True PASS')
else:
    raise SystemExit('expected --baseline or --modified')
