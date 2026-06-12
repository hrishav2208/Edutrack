import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

matches = re.findall(r'branch|Branch|BRANCH|edit.btn|edit-btn|Edit', html)
unique = list(set(matches))
print(unique[:30])
