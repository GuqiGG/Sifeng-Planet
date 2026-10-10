import requests

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com/',
})
session.get('https://www.bilibili.com/', timeout=15).raise_for_status()
search = session.get('https://api.bilibili.com/x/web-interface/search/type', params={
    'search_type': 'video', 'keyword': '雨爱 司凤', 'page': 1,
}, timeout=15).json()
bvid = next(row['bvid'] for row in search['data']['result'] if row.get('bvid'))
pages = session.get('https://api.bilibili.com/x/player/pagelist', params={'bvid': bvid}, timeout=15).json()
cid = pages['data'][0]['cid']
play = session.get('https://api.bilibili.com/x/player/playurl', params={
    'bvid': bvid, 'cid': cid, 'qn': 16, 'fnval': 0,
}, timeout=15).json()
assert search['code'] == pages['code'] == play['code'] == 0
assert play['data']['durl'][0]['url']
print('MOBILE_API: search=0 pagelist=0 playurl=0 mp4=True PASS')
