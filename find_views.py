import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
matches = re.findall(r'id=\"(admin-view-[^\"]+)\"', html)
print(set(matches))
