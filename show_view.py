with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
in_view = False
for line in lines:
    if 'id="admin-view-people"' in line:
        in_view = True
    if in_view:
        print(line.rstrip())
        if 'id="admin-view-campus"' in line:
            break
