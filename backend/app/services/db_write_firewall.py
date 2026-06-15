from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_DIR_PARTS = {"api", "routers", "adapters", "integrations", "workers"}
WRITE_METHODS = {"add", "add_all", "delete", "bulk_save_objects", "bulk_insert_mappings", "bulk_update_mappings", "merge"}
DB_SESSION_NAMES = {"db", "session"}
ALLOWED_PATH_PARTS = {"services", "repositories", "tests", "migrations", "scripts"}


def path_is_write_allowed(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & ALLOWED_PATH_PARTS) and not bool(parts & FORBIDDEN_DIR_PARTS - {"workers"})


def find_direct_db_write_violations(root: Path) -> list[str]:
    violations: list[str] = []
    for path in root.rglob("*.py"):
        if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
            continue
        rel = path.relative_to(root)
        if path_is_write_allowed(rel):
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                target = node.func.value
                target_name = target.id if isinstance(target, ast.Name) else ""
                if node.func.attr in WRITE_METHODS and target_name in DB_SESSION_NAMES:
                    violations.append(f"{rel}:{node.lineno} direct DB write via {target_name}.{node.func.attr}()")
    return violations
