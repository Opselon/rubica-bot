from __future__ import annotations

import ast


ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.UAdd,
    ast.USub,
    ast.Constant,
)


def safe_eval(expression: str) -> float:
    if len(expression) > 80:
        raise ValueError("عبارت خیلی طولانی است.")
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError("عبارت غیرمجاز است.")
    result = eval(compile(tree, "<safe_eval>", "eval"), {"__builtins__": {}})
    if isinstance(result, (int, float)):
        return float(result)
    raise ValueError("نتیجه نامعتبر است.")
