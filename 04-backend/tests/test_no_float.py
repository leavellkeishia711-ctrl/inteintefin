import ast
import pathlib
import pytest

FORBIDDEN_DIRS = ["app/services", "app/db/models", "app/api"]

def test_no_float_in_financial_code():
    offenders = []
    backend_dir = pathlib.Path(__file__).parent.parent
    for d in FORBIDDEN_DIRS:
        target_dir = backend_dir / d
        if not target_dir.exists():
            continue
        for path in target_dir.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "float":
                    offenders.append(f"{path}:{node.lineno}")
                if isinstance(node, ast.Constant) and isinstance(node.value, float):
                    offenders.append(f"{path}:{node.lineno} literal")
    assert not offenders, f"float РІ С„РёРЅР°РЅСЃРѕРІРѕРј РєРѕРґРµ: {offenders}"

