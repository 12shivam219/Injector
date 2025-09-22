import os
import re

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
paths = []
for base in ('ui', 'pages'):
    base_dir = os.path.join(root, base)
    if not os.path.isdir(base_dir):
        continue
    for dirpath, dirnames, filenames in os.walk(base_dir):
        for fn in filenames:
            if fn.endswith('.py'):
                paths.append(os.path.join(dirpath, fn))

results = []
for path in paths:
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    idx = 0
    while True:
        m = text.find('st.button(', idx)
        if m == -1:
            break
        # capture the arg block until matching parenthesis
        i = m + len('st.button(')
        depth = 1
        start = i
        while i < len(text) and depth>0:
            ch = text[i]
            if ch == '(':
                depth +=1
            elif ch == ')':
                depth -=1
            i+=1
        args = text[start:i-1]
        # determine if key= present
        has_key = 'key=' in args
        # find the line number
        line_no = text.count('\n', 0, m) + 1
        # extract a short preview of the line
        preview = '\n'.join(text.splitlines()[max(0,line_no-2):line_no+1])
        # suggest key
        # find label string literal if present
        label_match = re.search(r'st\.button\(\s*(f?"[^"]+"|f?\'[^\']+\')', text[m: i])
        if label_match:
            label = label_match.group(1)
            label_clean = re.sub(r"[^a-zA-Z0-9]", '_', label).strip('_').lower()
            suggested = os.path.splitext(os.path.basename(path))[0] + '_' + label_clean
            suggested = suggested[:80]
        else:
            suggested = os.path.splitext(os.path.basename(path))[0] + '_button'
        results.append((path, line_no, preview.strip(), has_key, suggested))
        idx = i

# Print results
for path, line_no, preview, has_key, suggested in results:
    print(f"FILE: {path}\nLINE: {line_no}\nHAS_KEY: {has_key}\nSUGGESTED_KEY: '{suggested}'\nPREVIEW:\n{preview}\n---\n")

print(f"Total scanned: {len(paths)} files. Found {len(results)} st.button occurrences.")
