import os

directory = r'c:\Users\PC\Desktop\PA_Frontend\PA_Frontend\frontend\src\pages'
for root, dirs, files in os.walk(directory):
    for file in files:
        if not file.endswith('.tsx'):
            continue
        filepath = os.path.join(root, file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if '\\\"' not in content:
            continue

        print(f'Fixing {filepath}')
        
        # Replace the backslash quotes
        content = content.replace('\\\"', '\"')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
