import typing as T
import orjson
from pydantic import BaseModel
from edge_orm.external import encoders
from edge_orm.node.models import Insert, Patch, CONVERSION_MAP

if T.TYPE_CHECKING:
    from .model import VARS


def model_to_set_str_vars(
    *, model: Insert | Patch, conversion_map: CONVERSION_MAP
) -> tuple[str, "VARS"]:
    """takes in a model dictionary and returns a string that represents a mutation with this dictionary
    eg: {"name": "Jeremy Berman", "age": UNSET, "last_updated": 2022...} -> { name := <str>$name, age := <int>{}, ...}"""
    str_lst: list[str] = []
    variables: VARS = {}
    for field_name in model.__fields_set__:
        if field_name not in conversion_map:
            print(f"{field_name=} not in conversion_map")
            continue
        type_cast = conversion_map[field_name].cast
        val = getattr(model, field_name)
        field_str = f"{field_name} := <{type_cast}>${field_name}"
        if isinstance(val, (dict, list)):
            if type_cast.endswith("::str") or type_cast.endswith("::json"):
                val = orjson.dumps(encoders.jsonable_encoder(val))
        elif isinstance(val, BaseModel):
            val = val.json()
        elif isinstance(val, set):
            val = list(val)
            field_str = (
                f"{field_name} := array_unpack(<array<{type_cast}>>${field_name})"
            )
        elif val is None:
            field_str = f"{field_name} := {{}}"
        str_lst.append(field_str)
        if val is not None:
            variables[field_name] = val

    s = f'{{ {", ".join(str_lst)} }}'
    return s, variables
