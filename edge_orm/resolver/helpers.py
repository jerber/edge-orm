import typing as T
import re


def replace_str_with_vars(s: str, variables: dict[str, T.Any]) -> str:
    if not s:
        return ""
    for var_name, var_val in variables.items():
        s = re.sub(
            rf"(\$)({var_name})(\W*)", r"\1" + f"[({var_val})]" + r"\3", s
        ).replace(f"[({var_val})]", f"{var_val}")
    return s
