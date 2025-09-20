import re
import pathlib
from importlib.metadata import PackageNotFoundError, version as get_version

root = pathlib.Path(__file__).resolve().parents[1]
req_path = root / 'requirements.txt'
text = req_path.read_text(encoding='utf-8')

pinned_lines = []
for raw in text.splitlines():
    s = raw.strip()
    if not s or s.startswith('#'):
        pinned_lines.append(raw)
        continue
    # Preserve inline comments with two-space convention
    if '  #' in raw:
        pkg_part, comment = raw.split('  #', 1)
        comment = '  #' + comment
    else:
        pkg_part, comment = raw, ''
    pkg_part = pkg_part.strip()

    # Extract name and extras (drop version markers)
    name_extras = re.split(r'[<>=!~ ]', pkg_part, 1)[0]
    if '[' in name_extras:
        name = name_extras.split('[', 1)[0]
        extras = name_extras[len(name):]
    else:
        name = name_extras
        extras = ''

    try:
        ver = get_version(name)
        pinned = f"{name}{extras}=={ver}{comment}"
    except PackageNotFoundError:
        # fallback: keep original line if package not installed
        pinned = raw
    pinned_lines.append(pinned)

print("\n".join(pinned_lines))
