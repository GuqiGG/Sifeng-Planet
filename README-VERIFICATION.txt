司凤星球 GitHub README / VERIFICATION / 2026-10-10
Changed branch/field: root README.md becomes Chinese-first GitHub product overview with five local screenshots, install/build instructions, English redirect, and noncommercial license link.
MODIFIED_FILE: C:\Users\guqig\Documents\Codex\2026-10-09\new-chat\README.md
DIFF_FILE: C:\Users\guqig\Documents\Codex\2026-10-09\new-chat\work\README.diff
VERIFICATION.txt: C:\Users\guqig\Documents\Codex\2026-10-09\new-chat\work\README-VERIFICATION.txt
ROLLBACK.sh: C:\Users\guqig\Documents\Codex\2026-10-09\new-chat\work\README-ROLLBACK.sh
English README: C:\Users\guqig\Documents\Codex\2026-10-09\new-chat\README.en.md
LICENSE: C:\Users\guqig\Documents\Codex\2026-10-09\new-chat\LICENSE
GitHub source ZIP: C:\Users\guqig\Documents\Codex\2026-10-09\new-chat\outputs\SiFengPlanet-GitHub-source.zip
Original README SHA256: 05693EB9D96A22AFF99CE3C844A38B1EFED11C2A4DBE9A0AC33ACEA55D5066F5
Modified README SHA256: 4ED08327216FC70CFC370FFA5EC1E7171847D7A463CE7A6C23BF3D67A5D6E96C
GitHub ZIP SHA256: FAE4D6F52F81A6CDA197835D8AE290AEAEBFDB5788876351FDA2B93CE0BFBD92

BASELINE
Command (workspace root): python work/verify_readme.py --baseline
Input: work/README.previous.md, preserved original outputs README
Literal output: BASELINE_README: image_previews=0 english_redirect=False PASS
Exit status: 0

MODIFIED
Command (workspace root): python work/verify_readme.py --modified
Input: README.md, README.en.md, LICENSE, and five docs/images PNG files
Literal output: MODIFIED_README: zh=True en_redirect=True previews=5 license=noncommercial links=valid PASS
Exit status: 0
Command (workspace root): python packaging command used to create outputs/SiFengPlanet-GitHub-source.zip
Input: 24 curated files including documentation, images, desktop and Android source
Literal output: GITHUB_SOURCE: files=24 zip=clean README=current PASS
Exit status: 0

ROLLBACK
Command (workspace root, Git Bash): work/README-ROLLBACK.sh work/README-rollback-copy.md
Input: separate copy of modified README.md
Literal output: ROLLBACK: previous README restored; sha256=05693eb9d96a22aff99ce3c844a38b1efed11c2a4dbe9a0ac33acea55d5066f5
Exit status: 0
Restored behavior/status: rollback copy matches original SHA256 05693EB9D96A22AFF99CE3C844A38B1EFED11C2A4DBE9A0AC33ACEA55D5066F5; MODIFIED_FILE remains changed with SHA256 4ED08327216FC70CFC370FFA5EC1E7171847D7A463CE7A6C23BF3D67A5D6E96C.

License selection: user chose a noncommercial license. LICENSE is the official PolyForm Noncommercial 1.0.0 plain text from https://polyformproject.org/licenses/noncommercial/1.0.0.txt; not MIT.
