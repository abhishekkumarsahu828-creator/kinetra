#!/usr/bin/env python3
"""Dependency-free source preflight. DOES NOT replace Django/PostgreSQL integration tests."""
import ast
import re
from pathlib import Path

root=Path(__file__).resolve().parents[1]
errors=[]
pyfiles=list(root.rglob('*.py'))
for p in pyfiles:
    try: ast.parse(p.read_text('utf-8'))
    except SyntaxError as e: errors.append(f'{p}: {e}')
urls=(root/'exchange/urls.py').read_text()+(root/'kinetra/urls.py').read_text()
known=set(re.findall(r"name=['\"]([a-z_]+)['\"]",urls))
htmlfiles=list((root/'templates').rglob('*.html'))
for p in htmlfiles:
    src=p.read_text('utf-8')
    for name in re.findall(r"{%\s*url\s+['\"]([a-z_]+)['\"]",src):
        if name not in known:errors.append(f'{p}: unknown URL {name}')
    tokens=re.findall(r'{%\s*(\w+)',src)
    for op,cl in [('if','endif'),('for','endfor'),('block','endblock')]:
        if tokens.count(op)!=tokens.count(cl):
            errors.append(f'{p}: unbalanced {op}/{cl}: {tokens.count(op)}/{tokens.count(cl)}')
    if src.count('{%')!=src.count('%}'):
        errors.append(f'{p}: unbalanced Django tag delimiters')
for file in ['manage.py','requirements.txt','Dockerfile','compose.yaml','compose.prod.yaml','.env.example',
             'exchange/migrations/0001_initial.py','docs/ARCHITECTURE.md']:
    if not (root/file).is_file():errors.append(f'Missing required file: {file}')
try:
    import yaml
    for name in ['compose.yaml','compose.prod.yaml']:
        parsed=yaml.safe_load((root/name).read_text())
        if 'services' not in parsed:errors.append(f'{name}: no services')
except ImportError:
    print('YAML parser unavailable (separate validation needed)')
print(f'Preflight inspected {len(pyfiles)} Python files, {len(htmlfiles)} Django templates, and {len(known)} route names.')
if errors:
    print('FAIL:')
    for item in errors:print(' -',item)
    raise SystemExit(1)
print('PASS: Python syntax, template tag balancing, URL references, required paths and YAML when available.')
print('NOT RUN: Django system checks, database migrations, HTTP flows, PostgreSQL concurrency, live browser testing.')
