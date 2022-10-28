import typing as T
import random
import string
import re

ALIAS_PATTERN = r">\$(\w+)"
RE_CODE = "04730"
SEPARATOR = "__"


ListType = T.TypeVar("ListType")


def random_str(n: int, include_re_code: bool = False) -> str:
    pre_str = RE_CODE if include_re_code else ""
    return pre_str + "".join(random.choices(string.ascii_letters + string.digits, k=n))


def random_digits(n: int) -> str:
    return "".join(random.choices(string.digits, k=n))


def chunk_list(lst: list[ListType], chunk_size: int) -> list[list[ListType]]:
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_list(lst: T.Iterable[T.Iterable[ListType]]) -> list[ListType]:
    return [j for sub in lst for j in sub]


def replace_str_with_vars(s: str, variables: dict[str, T.Any]) -> str:
    if not s:
        return ""
    for var_name, var_val in variables.items():
        s = re.sub(
            rf"(\$)({var_name})(\W*)", r"\1" + f"[({var_val})]" + r"\3", s
        ).replace(f"[({var_val})]", f"{var_val}")
    return s
