import pathlib
import sys

old = pathlib.Path('outputs/PREVIOUS_VERSION.java').read_text(encoding='utf-8')
new = pathlib.Path('mobile/app/src/main/java/com/sifeng/planet/MainActivity.java').read_text(encoding='utf-8')
if sys.argv[1] == '--baseline':
    assert 'Collections.shuffle(found);' in old
    assert 'searchCount' not in old
    assert '&avid=' not in old
    print('BASELINE_MOBILE: unconditional_shuffle=True avid_fallback=False PASS')
elif sys.argv[1] == '--modified':
    assert 'final boolean popular=(++searchCount%2)==1' in new
    assert 'if(popular)found.sort' in new and 'else Collections.shuffle(found)' in new
    assert 'popular?"&order=click":""' in new
    assert new.index('if(popular)found.sort') < new.index('if(found.size()>36)found.subList')
    assert '&avid=' in new and 'for(String candidate:urlsToTry)' in new
    print('MODIFIED_MOBILE: alternating_hot_random=True avid_fallback=True PASS')
else:
    raise SystemExit('expected --baseline or --modified')
