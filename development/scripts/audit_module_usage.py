"""Inspect local module references without importing or executing project code."""
from pathlib import Path
import ast
import json
import subprocess
import tokenize


def audit(root):
    names = subprocess.check_output(
        ['git', 'ls-files', '-co', '--exclude-standard', '-z'], cwd=root
    ).decode('utf-8').split('\0')
    paths = sorted({name for name in names if name.endswith('.py')
                    and name.startswith(('backend/', 'development/scripts/', 'development/tests/'))
                    and (root / name).is_file()})

    def module(name):
        return name.removeprefix('backend/').removesuffix('.py').replace('/', '.').removesuffix('.__init__')

    modules = {module(name): name for name in paths if name.startswith('backend/')}
    edges, errors, dynamic = {}, [], []
    for name in paths:
        try:
            with tokenize.open(root / name) as source:
                tree = ast.parse(source.read())
        except (UnicodeError, SyntaxError) as error:
            errors.append({'path': name, 'error': str(error)})
            continue
        own = module(name)
        package = own.split('.') if name.endswith('/__init__.py') else own.split('.')[:-1]
        dependencies = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                dependencies.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                parent = package[:-(node.level - 1)] if node.level > 1 else package
                base = '.'.join([*parent, *([node.module] if node.module else [])]) if node.level else node.module or ''
                dependencies.add(base)
                dependencies.update('.'.join(value for value in (base, alias.name) if value) for alias in node.names)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                target = node.value.split(':', 1)[0]
                if target in modules and target != own:
                    dependencies.add(target)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module':
                if not node.args or not isinstance(node.args[0], ast.Constant):
                    dynamic.append({'path': name, 'line': node.lineno, 'call': ast.unparse(node)})
        dependencies = {value for value in dependencies if value in modules}
        dependencies.update('.'.join(own.split('.')[:depth]) for depth in range(1, len(own.split('.')))
                            if '.'.join(own.split('.')[:depth]) in modules)
        edges[own] = dependencies

    entries = {'web_api', 'stockrl.__main__', 'stockrl.job_worker',
               'stockrl.finrl.policy_learning.official_cli', 'stockrl.platform.kiwoom_worker'}
    checks = {module(name) for name in paths if name.startswith(('development/scripts/', 'development/tests/'))}

    def reach(initial):
        seen, queue = set(initial), list(initial)
        while queue:
            for target in edges.get(queue.pop(), ()):
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        return seen

    operating = reach(entries)
    retained = reach(entries | checks)
    return {'analysis_kind': 'static_reference_graph', 'execution_verified': False,
            'nonuse_verdict': 'unconfirmed', 'python_files': len(paths),
            'production_referenced': sorted(path for name, path in modules.items() if name in operating),
            'inspection_only': sorted(path for name, path in modules.items() if name in retained - operating),
            'unreferenced_candidates': sorted(path for name, path in modules.items() if name not in retained and not path.endswith('/__init__.py')),
            'source_errors': errors, 'dynamic_imports_for_review': dynamic,
            'note': 'Static references only; candidates are not proven unused. Dynamic imports, conditional imports and string references require review. No project imports, function execution, authentication checks or deletion.'}


if __name__ == '__main__':
    import shutil
    import sys
    if not shutil.which('git'):
        raise SystemExit('Git executable must be on PATH.')
    result = audit(Path(__file__).resolve().parents[2])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(bool(result['source_errors']))
