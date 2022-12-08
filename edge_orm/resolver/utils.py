import typing as T
import json
from enum import Enum
from pydantic import BaseModel
from edge_orm.external import encoders
from edge_orm.node.models import Insert, Patch, CONVERSION_MAP, FieldInfo
from edge_orm.resolver import errors, enums

if T.TYPE_CHECKING:
    from .model import VARS
    from .model import Resolver

ResolverType = T.TypeVar("ResolverType", bound="Resolver")


def line_var_from_field_info(
    field_name: str, val: T.Any, field_info: FieldInfo, json_get_item: str = None
) -> tuple[str, T.Any]:
    type_cast = field_info.cast
    var_field_name = (
        f"${field_name}"
        if not json_get_item
        else f'json_get({json_get_item}, "{field_name}")'
    )
    field_str = f"{field_name} := <{type_cast}>{var_field_name}"
    if isinstance(val, (dict, list)):
        if type_cast.endswith("::str") or type_cast.endswith("::json"):
            val = json.dumps(encoders.jsonable_encoder(val))
    elif isinstance(val, BaseModel):
        val = val.json()
    elif isinstance(val, set):
        val = list(val)
        field_str = (
            f"{field_name} := array_unpack(<array<{type_cast}>>{var_field_name})"
        )
    elif isinstance(val, Enum):
        val = val.value
    elif val is None and not json_get_item:
        field_str = f"{field_name} := {{}}"
    return field_str, val


def line_var_from_resolver(
    model: Insert | Patch, field_name: str, r: ResolverType
) -> tuple[str, T.Any]:
    if isinstance(model, Patch):
        if r.update_operation is None:
            raise errors.ResolverException(
                "Link resolvers for Patch objects must have an update operation."
            )
    elif isinstance(model, Insert):
        if r.update_operation is None:
            r.update_operation = enums.UpdateOperation.REPLACE
        if r.update_operation != enums.UpdateOperation.REPLACE:
            errors.ResolverException(
                "Update operations for link resolvers for Insert objects cannot be anything "
                "other than None or REPLACE."
            )
    else:
        errors.ResolverException("Model must be either an Insert or Patch.")
    rez_s, rez_vars = r.full_query_str_and_vars(
        prefix=field_name, include_select=True, include_detached=True
    )
    s = f"{field_name} {r.update_operation.value} ({rez_s})"
    return s, rez_vars


def model_to_set_str_vars(
    *,
    model: Insert | Patch,
    conversion_map: CONVERSION_MAP,
    json_get_item: str = None,
    additional_link_str: str | None = None,
) -> tuple[str, "VARS"]:
    """takes in a model dictionary and returns a string that represents a mutation with this dictionary
    eg: {"name": "Jeremy Berman", "age": UNSET, "last_updated": 2022...} -> { name := <str>$name, age := <int>{}, ...}"""
    str_lst: list[str] = []
    variables: VARS = {}
    for field_name in model.set_fields_:
        original_val = getattr(model, field_name)
        if field_name not in conversion_map:
            # this is a resolver
            rez_s, rez_vars = line_var_from_resolver(
                model=model, field_name=field_name, r=original_val
            )
            str_lst.append(rez_s)
            variables.update(rez_vars)
        else:
            field_str, val = line_var_from_field_info(
                field_name=field_name,
                val=original_val,
                field_info=conversion_map[field_name],
                json_get_item=json_get_item,
            )
            str_lst.append(field_str)
            if val is not None:
                variables[field_name] = val

    if additional_link_str:
        str_lst.append(additional_link_str)
    s = f'{{ {", ".join(str_lst)} }}'
    return s, variables
