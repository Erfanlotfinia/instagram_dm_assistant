from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_DIR_PARTS = {"api", "routers", "adapters", "integrations", "llm", "automation"}
WRITE_METHODS = {
    "add",
    "add_all",
    "delete",
    "commit",
    "flush",
    "execute",
    "bulk_save_objects",
    "bulk_insert_mappings",
    "bulk_update_mappings",
    "merge",
}
DB_SESSION_NAMES = {"db", "session"}
ALLOWED_PATH_PARTS = {"services", "repositories", "tests", "migrations", "scripts", "workers"}
READ_ONLY_SQL_PREFIXES = ("select", "show", "explain")


def path_is_write_allowed(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & ALLOWED_PATH_PARTS) and not bool(parts & FORBIDDEN_DIR_PARTS)


def _literal_sql(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.strip().lower()
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "text" and node.args:
        return _literal_sql(node.args[0])
    return None


def _is_read_only_execute(node: ast.Call) -> bool:
    if not node.args:
        return False
    sql = _literal_sql(node.args[0])
    return bool(sql and sql.startswith(READ_ONLY_SQL_PREFIXES))


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
                if target_name not in DB_SESSION_NAMES or node.func.attr not in WRITE_METHODS:
                    continue
                if node.func.attr == "execute" and _is_read_only_execute(node):
                    continue
                violations.append(f"{rel}:{node.lineno} direct DB write via {target_name}.{node.func.attr}()")
    return violations
