import os
import re

directory = r'c:\Users\PC\Desktop\PA_Frontend\PA_Frontend\frontend\src\pages'
for root, dirs, files in os.walk(directory):
    for file in files:
        if not file.endswith('.tsx'):
            continue
        filepath = os.path.join(root, file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if '<Sidebar' not in content:
            continue

        print(f'Fixing {filepath}')
        
        # Remove imports
        content = re.sub(r'import\s+\{\s*Sidebar\s*\}\s+from\s+[^;]+;\n', '', content)
        content = re.sub(r'import\s+\{\s*Header\s*\}\s+from\s+[^;]+;\n', '', content)
        
        # We replace the app-shell structure. Sometimes it is `page-content max-w-2xl mx-auto` etc.
        # Match <div className="app-shell"> ... </div>
        # Note: parsing HTML with regex is brittle, but since it's a very consistent wrapper:
        content = re.sub(r'<div className=\"app-shell\">\s*<Sidebar[^>]*/>\s*<div className=\"app-main\">\s*<Header[^>]*/>\s*<main className=\"page-content[^\"]*\">\s*(.*?)\s*</main>\s*</div>\s*</div>', r'<div className=\"max-w-7xl mx-auto w-full pb-10\">\n\1\n</div>', content, flags=re.DOTALL)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
