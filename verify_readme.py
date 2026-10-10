import pathlib
import re
import struct
import sys
import xml.etree.ElementTree as ET

root = pathlib.Path('.')
readme = (root / 'README.md').read_text(encoding='utf-8-sig')
english = (root / 'README.en.md').read_text(encoding='utf-8-sig')
license_text = (root / 'LICENSE').read_text(encoding='utf-8-sig')

if sys.argv[1] == '--baseline':
    old = (root / 'work/README.previous.md').read_text(encoding='utf-8-sig')
    assert '<table>' in old and 'brand.svg' not in old
    print('BASELINE_README: table_layout=True brand_mark=False PASS')
elif sys.argv[1] == '--modified':
    assert '司凤星球' in readme and 'README.en.md' in readme
    assert 'README.md' in english and 'PolyForm Noncommercial' in english
    assert license_text.startswith('# PolyForm Noncommercial License 1.0.0')
    assert '## Noncommercial Purposes' in license_text
    assert '<table>' not in readme and '<details>' in readme
    assert './docs/images/brand.svg' in readme
    assert ET.parse(root / 'docs/images/brand.svg').getroot().tag.endswith('svg')
    images = re.findall(r'(?:src="|!\[[^]]*\]\()(\./docs/images/[^)\"]+)', readme)
    assert len(images) == 5
    for item in images:
        path = root / item
        data = path.read_bytes()
        assert data[:8] == b'\x89PNG\r\n\x1a\n'
        width, height = struct.unpack('>II', data[16:24])
        assert width >= 300 and height >= 70
    for link in ('README.en.md', 'LICENSE', 'outputs/requirements.txt', 'outputs/sifeng_planet.pyw'):
        assert (root / link).is_file()
    print('MODIFIED_README: editorial_layout=True previews=5 brand_mark=True links=valid PASS')
else:
    raise SystemExit('expected --baseline or --modified')
