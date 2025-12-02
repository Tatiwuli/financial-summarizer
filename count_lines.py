import os
import re

def count_code_lines(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total = len(lines)
    imports = 0
    blank = 0
    comments = 0
    code = 0
    
    in_multiline_comment = False
    multiline_comment_lines = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Check for multiline comments (/* ... */)
        if '/*' in line:
            in_multiline_comment = True
            multiline_comment_lines += 1
            if '*/' in line:
                in_multiline_comment = False
            continue
            
        if in_multiline_comment:
            multiline_comment_lines += 1
            if '*/' in line:
                in_multiline_comment = False
            continue
        
        # Empty line
        if not stripped:
            blank += 1
        # Single-line comment
        elif stripped.startswith('//'):
            comments += 1
        # Import/export statement
        elif stripped.startswith('import ') or stripped.startswith('from ') or stripped.startswith('export '):
            imports += 1
        # Actual code
        else:
            code += 1
    
    return {
        'total': total,
        'imports': imports,
        'blank': blank,
        'comments': comments,
        'multiline_comments': multiline_comment_lines,
        'code': code
    }

paths = ['components/common', 'components/results/common', 'components/specific','screens', 'services','state','types', '']
# Target directory - recursively find all .ts and .tsx files
for path in paths:
    target_dir = 'summarizer-app/src/' + path
    ts_files = []

    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.ts') or file.endswith('.tsx'):
                file_path = os.path.join(root, file)
                ts_files.append(file_path)

    print('=' * 80)
    print('TYPESCRIPT CODE LINE COUNT ANALYSIS (excluding imports)')
    print('=' * 80)
    print()

    total_code = 0
    results = []

    for file_path in sorted(ts_files):
        counts = count_code_lines(file_path)
        results.append((file_path, counts))
        total_code += counts['code']
        
    for file_path, counts in results:
        # Display relative path from target_dir
        display_path = file_path.replace(target_dir + os.sep, '')
        print(f'{display_path}')
        print(f'  Total lines:          {counts["total"]:>4}')
        print(f'  Import/export:        {counts["imports"]:>4}')
        print(f'  Blank lines:          {counts["blank"]:>4}')
        print(f'  Comment lines:        {counts["comments"]:>4}')
        print(f'  Multiline comments:   {counts["multiline_comments"]:>4}')
        print(f'  ACTUAL CODE LINES:    {counts["code"]:>4}')
        print()

    print('=' * 80)
    print(f'TOTAL ACTUAL CODE LINES (all files): {total_code}')
    print('=' * 80)
