import re
import typing as T
from enum import Enum
import os
from pathlib import Path
from black import format_str, FileMode
import edgedb
from pydantic import BaseModel, parse_raw_as, Field
from .introspection import (
    introspect_objects,
    introspect_scalars,
    ObjectType,
    Link,
    Property,
)
from edge_orm.node.models import (
    CONVERSION_MAP,
    PropertyCardinality,
    FieldInfo,
    Cardinality,
)

ENV_VAR_PATTERN = r"[A-Z_]+"
COUNT_POSTFIX = "_Count"


class DBVendor(str, Enum):
    edgedb = "edgedb"


class PropertyConfig(BaseModel):
    module_path: str
    module_name: str
    validate_as_basemodel: bool = True
    cardinality: PropertyCardinality = PropertyCardinality.ONE


class NodeConfig(BaseModel):
    module_path: str | None = None
    insert_path: str | None = None
    patch_path: str | None = None

    appendix_properties: T.List[str] = []
    ignore_properties: T.List[str] = []
    basemodel_properties: T.Dict[str, PropertyConfig] = {}
    custom_annotations: T.Dict[str, str] = {}
    mutate_on_update: T.Dict[str, str] = {}


class DBConfig(BaseModel):
    vendor: DBVendor
    dsn_: str = Field(..., alias="dsn")
    copy_config: str | None = None
    hydrate: bool = False
    nodes: T.Dict[str, NodeConfig] = dict()
    cache_only: bool = True
    resolver_mixin_path: str | None = None

    @property
    def is_plaintext_dsn(self) -> bool:
        return self.dsn_.startswith("edgedb://")

    @property
    def dsn(self) -> str:
        if self.is_plaintext_dsn:
            return self.dsn_
        return os.environ[self.dsn_]

    def dsn_str(self) -> str:
        if self.is_plaintext_dsn:
            return f'"{self.dsn_}"'
        return f'os.environ["{self.dsn_}"]'


PATH_TO_MODULE = "edge_orm"
DEFAULT_INDENT = "    "
CONFIG_NAME = "GraphORM"


class GeneratorException(Exception):
    pass


def indent_lines(s: str, indent: str = DEFAULT_INDENT) -> str:
    chunks = s.split("\n")
    return indent + f"\n{indent}".join(chunks)


def imports(enums_module: str, resolver_mixin_path: str | None) -> str:
    lines = [
        "from __future__ import annotations",
        "import os",
        "import typing as T",
        "from enum import Enum",
        "from datetime import datetime, date, timedelta",
        "from uuid import UUID",
        "from decimal import Decimal",
        "from edgedb import RelativeDuration, AsyncIOClient, create_async_client",
        "from pydantic import BaseModel, Field, PrivateAttr, validator",
        f"from {PATH_TO_MODULE}.node.models import Cardinality, FieldInfo, classproperty",
        f"from {PATH_TO_MODULE} import Node, Insert, Patch, EdgeConfigBase, Resolver, NodeException, ResolverException, UNSET, UnsetType, validators, errors, resolver_enums",
        "FilterConnector = resolver_enums.FilterConnector",
        f"from . import {enums_module} as enums",
    ]
    if resolver_mixin_path:
        lines.append(resolver_mixin_path)
    return "\n".join(lines)


def build_enum_imports() -> str:
    lines = ["from enum import Enum"]
    return "\n".join(lines)


async def build_enums(client: edgedb.AsyncIOClient, include_strawberry: bool) -> str:
    scalar_types = await introspect_scalars(client)
    enum_strs: T.List[str] = []
    enum_names: T.List[str] = []
    for scalar in scalar_types:
        if not scalar.enum_values:
            continue
        enum_value_strs: T.List[str] = [f'{e} = "{e}"' for e in scalar.enum_values]
        enum_value_str = "\n".join(enum_value_strs)
        s = f"class {scalar.node_name}(str, Enum):\n{indent_lines(enum_value_str)}"
        enum_strs.append(s)
        enum_names.append(scalar.node_name)
    if include_strawberry:
        straw_enums_str = "\n".join(
            [f"{enum_name} = strawberry.enum({enum_name})" for enum_name in enum_names]
        )
        straw_lines = [
            "import strawberry",
            f"class Strawberry:\n{indent_lines(straw_enums_str)}",
        ]
        enum_strs.extend(straw_lines)
    return "\n".join(enum_strs)


def build_node_link_function_str(link: Link) -> str:
    link_resolver_name = f"{link.target.model_name}Resolver"
    normal = f"""
async def {link.name}(
    self,
    resolver: {link_resolver_name} = None,
    cache_only: bool = CACHE_ONLY,
    client: AsyncIOClient | None = None,
) -> {link.type_str.replace("enums.", "")}:
    return await self.resolve(
        edge_name="{link.name}",
        edge_resolver=resolver or {link_resolver_name}(),
        cache_only=cache_only,
        client=client,
    )
"""
    count = f"""
async def {link.name}{COUNT_POSTFIX}(
    self,
    resolver: {link_resolver_name} = None,
    cache_only: bool = CACHE_ONLY,
    client: AsyncIOClient | None = None
) -> int:
    rez = resolver or {link_resolver_name}()
    rez.is_count = True
    return await self.resolve(
        edge_name="{link.name}{COUNT_POSTFIX}",
        edge_resolver=rez,
        cache_only=cache_only,
        client=client,
    )
    """
    s = normal
    if link.cardinality == Cardinality.Many:
        s += f"\n{count}"
    return s


def build_resolver_link_function_str(node_resolver_name: str, link: Link) -> str:
    link_resolver_name = f"{link.target.model_name}Resolver"
    normal = f"""
def {link.name}(self, _: T.Optional[{link_resolver_name}] = None, /, make_first: bool = False) -> {node_resolver_name}:
    self._nested_resolvers.add("{link.name}", _ or {link_resolver_name}(), make_first=make_first)
    return self
    """
    count = f"""
def {link.name}{COUNT_POSTFIX}(self, _: T.Optional[{link_resolver_name}] = None, /, make_first: bool = False) -> {node_resolver_name}:
    rez = _ or {link_resolver_name}()
    rez.is_count = True
    self._nested_resolvers.add(
        "{link.name}{COUNT_POSTFIX}",
        rez,
        make_first=make_first
    )
    return self
    """
    s = normal
    if link.cardinality == Cardinality.Many:
        s += f"\n{count}"
    return s


def build_exclusive_functions_str(
    node_name: str, exclusive_field_names: T.Set[str]
) -> str:
    exclusive_field_names_lst = sorted(list(exclusive_field_names))
    params_fields_str = ", ".join(
        [f"{f}: T.Optional[T.Any] = None" for f in exclusive_field_names_lst]
    )
    dict_fields_str = ", ".join([f'"{f}": {f}' for f in exclusive_field_names_lst])

    validation_str = f"""
kwargs = {{{dict_fields_str}}}
kwargs = {{k: v for k, v in kwargs.items() if v is not None}}
if len(kwargs) != 1:
    raise ResolverException(
        f"Must only give one argument, received {{kwargs}}."
    )
field_name, value = list(kwargs.items())[0]
""".strip()

    get_str = f"""
async def get(self, *, client: AsyncIOClient | None = None, {params_fields_str}) -> {node_name} | None:
{indent_lines(validation_str)}
    return await self._get(field_name=field_name, value=value, client=client)
    """
    gerror_str = f"""
async def gerror(self, *, client: AsyncIOClient | None = None, {params_fields_str}) -> {node_name}:
{indent_lines(validation_str)}
    return await self._gerror(field_name=field_name, value=value, client=client)
    """
    update_one_str = f"""
async def update_one(self, patch: {node_name}Patch, *, client: AsyncIOClient | None = None, {params_fields_str}) -> {node_name}:
{indent_lines(validation_str)}
    return await self._update_one(patch=patch, field_name=field_name, value=value, client=client)
    """
    delete_one_str = f"""
async def delete_one(self, *, client: AsyncIOClient | None = None, {params_fields_str}) -> {node_name}:
{indent_lines(validation_str)}
    return await self._delete_one(field_name=field_name, value=value, client=client)
    """
    return f"{get_str}\n{gerror_str}\n{update_one_str}\n{delete_one_str}\n"


def build_include_fields_function(
    node_resolver_name: str,
    appendix_properties: set[str],
    computed_properties: set[str],
) -> str:
    field_names = sorted({*appendix_properties, *computed_properties})
    names_params = ", ".join([f"{name}: bool = False" for name in field_names])
    logic_strs = "\n".join(
        [
            f'if {field_name} is True: fields_to_include.add("{field_name}")'
            for field_name in field_names
        ]
    )
    if not names_params:
        return ""
    s = f"""
def include(self, *, {names_params}) -> {node_resolver_name}:
    fields_to_include: set[str] = set()
{indent_lines(logic_strs)}
    return self.include_fields(*fields_to_include)
    """
    return s


def build_filter_functions_str(node_name: str, conversion_map: CONVERSION_MAP) -> str:
    field_names = sorted(conversion_map.keys())
    params_fields_str = ", ".join(
        [f"{f}: T.Optional[T.Any] = None" for f in field_names]
    )
    dict_fields_str = ", ".join([f'"{f}": {f}' for f in field_names])
    filter_by_str = f"""
def filter_by(self, filter_connector: FilterConnector = FilterConnector.AND, {params_fields_str}) -> {node_name}Resolver:
    return self._filter_by(connector=filter_connector, **{{{dict_fields_str}}})
    """
    # now for filter in
    params_fields_lst_str = ", ".join(
        [f"{f}: T.Optional[T.List[T.Any]] = None" for f in field_names]
    )
    filter_in_str = f"""
def filter_in(self, filter_connector: FilterConnector = FilterConnector.AND, {params_fields_lst_str}) -> {node_name}Resolver:
    return self._filter_in(connector=filter_connector, **{{{dict_fields_str}}})
    """
    return f"{filter_by_str}\n{filter_in_str}"


def add_quotes(lst: T.Iterable[str]) -> T.Iterable[str]:
    return [f'"{o}"' for o in lst]


def build_orm_config(
    model_name: str,
    updatable_fields: set[str],
    exclusive_fields: set[str],
    appendix_properties: set[str],
    computed_properties: set[str],
    basemodel_properties: T.Iterable[str],
    custom_annotations: T.Iterable[str],
    mutate_on_update: dict[str, str],
    node_edgedb_conversion_map: CONVERSION_MAP,
    insert_edgedb_conversion_map: CONVERSION_MAP,
    patch_edgedb_conversion_map: CONVERSION_MAP,
    insert_link_conversion_map: CONVERSION_MAP,
) -> str:
    return f"""
EdgeConfig: T.ClassVar[EdgeConfigBase] = EdgeConfigBase(
    model_name = "{model_name}",
    client = CLIENT,

    updatable_fields = {{{', '.join(add_quotes(sorted(list(updatable_fields))))}}},
    exclusive_fields = {{{', '.join(add_quotes(sorted(list(exclusive_fields))))}}},

    appendix_properties = {stringify_set(appendix_properties)},
    computed_properties = {stringify_set(computed_properties)},
    basemodel_properties = {stringify_set(set(basemodel_properties))},
    custom_annotations = {stringify_set(set(custom_annotations))},
    mutate_on_update = {stringify_dict(mutate_on_update)},

    node_edgedb_conversion_map = {stringify_basemodel_dict(node_edgedb_conversion_map)},
    insert_edgedb_conversion_map = {stringify_basemodel_dict(insert_edgedb_conversion_map)},
    patch_edgedb_conversion_map = {stringify_basemodel_dict(patch_edgedb_conversion_map)},

    insert_link_conversion_map = {stringify_basemodel_dict(insert_link_conversion_map)}
)
    """


def stringify_dict(
    d: T.Union[T.Dict[str, T.Any], str | bool], stringify_value: bool = True
) -> str:
    if type(d) is not dict:
        s = f"{d}"
        if type(d) is not bool:
            if stringify_value:
                s = f'"{s}"'
        return s
    inner = [
        f'"{k}":{stringify_dict(v, stringify_value=stringify_value)}'
        for k, v in d.items()
    ]
    return f"{{{','.join(inner)}}}"


def stringify_set(s: T.Set[str]) -> str:
    if not s:
        return "set()"
    s_sorted = sorted(list(s))
    strs: T.List[str] = [f'"{i}"' for i in s_sorted]
    return "{" + ",".join(strs) + "}"


def stringify_basemodel(model: BaseModel) -> str:
    "FieldInfo{cast: <str>} -> FieldInfo(cast='<str>')"
    str_lst: list[str] = []
    for k, v in model.dict().items():
        val_str = v
        if isinstance(v, Enum):
            val_str = f"{v.__class__.__name__}.{v.value}"
        elif isinstance(v, str):
            val_str = f'"{v}"'
        elif isinstance(v, BaseModel):
            val_str = stringify_basemodel(v)
        str_lst.append(f"{k}={val_str}")
    inner = ", ".join(str_lst)
    return f"{model.__class__.__name__}({inner})"


BaseModelType = T.TypeVar("BaseModelType", bound=BaseModel)


def stringify_basemodel_dict(d: dict[str, BaseModelType]) -> str:
    inner = [f'"{k}":{stringify_basemodel(v)}' for k, v in d.items()]
    return f"{{{','.join(inner)}}}"


def edgedb_conversion_type_from_prop(prop: Property, get_base: bool = False) -> str:
    """
    s = prop.target.name
    pattern = r"default::\w+"
    s = re.sub(pattern, "std::str", s)
    return s
    """
    if get_base:
        if prop.target.name.startswith("default::") and prop.target.bases:
            return prop.target.bases[0].name
    return prop.target.name


def build_validator_module_imports(db_config: DBConfig) -> str:
    if not db_config.nodes:
        return ""
    node_configs = db_config.nodes.values()
    from_str_import_strs: T.List[str] = []
    for node_config in node_configs:
        for prop_name, prop_config in node_config.basemodel_properties.items():
            from_str_import_strs.append(
                f"from {prop_config.module_path} import {prop_config.module_name}"
            )
    return "\n".join(sorted(list(set(from_str_import_strs))))


def key_from_field_name(f_name: str, node_config: NodeConfig) -> str:
    k = f_name
    if f_name in node_config.appendix_properties:
        k += "_"
    return f'"{k}"'


def build_from_str_validator_str(node_config: NodeConfig | None) -> str:
    if node_config is None:
        return ""
    field_name_strs: T.List[str] = []

    for field_name in node_config.custom_annotations.keys():
        field_name_strs.append(key_from_field_name(field_name, node_config=node_config))
    for field_name, props_config in node_config.basemodel_properties.items():
        if props_config.validate_as_basemodel is False:
            continue
        field_name_strs.append(key_from_field_name(field_name, node_config=node_config))
    if not field_name_strs:
        return ""
    return f"""
_from_str = validator({", ".join(field_name_strs)}, pre=True, allow_reuse=True)(validators.from_str)
    """


ListType = T.TypeVar("ListType")


def remove_falsies(lst: list[ListType]) -> list[ListType]:
    return [i for i in lst if i]


class InsertPatch(str, Enum):
    INSERT = "Insert"
    PATCH = "Patch"


def insert_patch_str(
    is_hydrated: bool,
    property_strs: list[str],
    model_name: str,
    insert_patch: InsertPatch,
) -> str:
    if is_hydrated:
        inherits = f"{model_name}Hydrated"
        rez_strs = [s for s in property_strs if "Resolver" in s]
        if not rez_strs:
            inner_str = indent_lines("pass")
        else:
            inner_str = indent_lines("\n".join(rez_strs))
    else:
        inherits = insert_patch.value
        inner_str = indent_lines("\n".join(property_strs))
    return f"class {model_name}({inherits}):\n{inner_str}"


def build_node_and_resolver(
    object_type: ObjectType,
    node_config: T.Optional[NodeConfig],
    edge_resolver_map_strs: T.List[str],
    hydrate: bool,
    insert_hydrate: bool,
    patch_hydrate: bool,
    dehydrate: bool,
    allow_inserting_id: bool = True,
    resolver_mixin_model: str | None = None,
) -> str:
    is_hydrate = hydrate or insert_hydrate or patch_hydrate
    # need to sort props and links by required, exclusive, no default, rest
    object_type.properties.sort(
        key=lambda x: f"{not x.is_computed}-{x.required}-{x.is_exclusive}-{x.default}",
        reverse=True,
    )
    object_type.links.sort(
        key=lambda x: f"{not x.is_computed}-{x.required}-{x.is_exclusive}-{x.default}",
        reverse=True,
    )
    # remove ignored properties
    if node_config:
        object_type.properties = [
            p
            for p in object_type.properties
            if p.name not in node_config.ignore_properties
        ]

    # start with the properties
    node_resolver_name = f"{object_type.node_name}Resolver"
    property_strs: T.List[str] = []
    insert_property_strs: T.List[str] = []
    patch_property_strs: T.List[str] = []
    updatable_fields: T.Set[str] = set()
    exclusive_fields: T.Set[str] = set()

    node_edgedb_conversion_map: CONVERSION_MAP = {}
    insert_edgedb_conversion_map: CONVERSION_MAP = {}
    patch_edgedb_conversion_map: CONVERSION_MAP = {}

    computed_properties: T.Set[str] = set()
    computed_property_getter_strs: T.List[str] = []

    appendix_properties: T.Set[str] = set()

    for prop in object_type.properties:
        conversion_type = edgedb_conversion_type_from_prop(prop)
        base_conversion_type = edgedb_conversion_type_from_prop(prop, get_base=True)
        node_edgedb_conversion_map[prop.name] = FieldInfo(
            cast=conversion_type,
            base_cast=base_conversion_type,
            cardinality=prop.cardinality,
            readonly=prop.readonly,
            required=prop.required,
        )
        if prop.is_computed:
            computed_properties.add(prop.name)
        is_appendix = False
        if node_config:
            if prop.name in node_config.appendix_properties:
                is_appendix = True
                appendix_properties.add(prop.name)
        if not prop.readonly and not prop.is_computed:
            updatable_fields.add(prop.name)
        if prop.is_exclusive:
            exclusive_fields.add(prop.name)
        default_value_str = "..." if prop.required else "None"
        # allow_mutation_str = (
        #     f"allow_mutation={not prop.readonly and not prop.is_computed}"
        # )
        if node_config and prop.name in node_config.basemodel_properties:
            prop_config = node_config.basemodel_properties[prop.name]
            module_name = prop_config.module_name
            type_str = prop.type_str_basemodel(
                module_name, cardinality=prop_config.cardinality
            )
        elif node_config and prop.name in node_config.custom_annotations:
            type_str = prop.type_str.replace(
                "str", node_config.custom_annotations[prop.name]
            )
        else:
            type_str = prop.type_str
        if not (prop.is_computed or is_appendix):
            property_strs.append(
                f"{prop.name}: {type_str} = Field({default_value_str})"
            )
        else:
            if prop.is_computed:
                exception_name = "ComputedPropertyException"
                # property_name = f"_{prop.name}"
                # property_str = f"{property_name}: T.Union[{type_str}, UnsetType] = PrivateAttr(UNSET)"
                property_name = f"{prop.name}_"
                property_str = f'{property_name}: T.Union[{type_str}, UnsetType] = Field(UNSET, alias="{prop.name}")'
            else:
                exception_name = "AppendixPropertyException"
                property_name = f"{prop.name}_"
                property_str = f'{property_name}: T.Union[{type_str}, UnsetType] = Field(UNSET, alias="{prop.name}")'
            exception_name = f"errors.{exception_name}"
            property_strs.append(property_str)
            val_str = "val"
            if "Set[" in type_str:
                val_str = f"val if type(val) != list else set(val)"
            computed_property_getter_strs.append(
                f"""
@property
def {prop.name}(self) -> {type_str}:
    # if self.{property_name} is UNSET:
    if "{property_name}" not in self.set_fields_:
            raise {exception_name}("{prop.name} is unset")
    return self.{property_name} # type: ignore
                """
            )
        #             if not prop.is_computed:
        #                 computed_property_getter_strs.append(
        #                     f"""
        # @{prop.name}.setter
        # def {prop.name}(self, {prop.name}: {type_str}) -> None:
        #     self.{property_name} = {prop.name}
        #                     """
        #                 )
        if prop.name != "id" or allow_inserting_id:
            # for insert type
            if not prop.is_computed and not prop.not_insertable:
                insert_edgedb_conversion_map[prop.name] = FieldInfo(
                    cast=conversion_type,
                    base_cast=base_conversion_type,
                    cardinality=prop.cardinality,
                    readonly=prop.readonly,
                    required=prop.required,
                )
                insert_type_str = type_str
                # if required but has default, add optional back
                if prop.required and prop.default:
                    # insert_type_str = f"T.Optional[{insert_type_str}]"
                    insert_type_str = f"T.Union[{insert_type_str}, UnsetType]"
                if insert_type_str.startswith("T.Optional["):
                    insert_type_str_test = (
                        "T.Union[" + insert_type_str[11:-1] + ", None, UnsetType]"
                    )
                    insert_type_str = insert_type_str_test
                default_value_str = (
                    " = Field(UNSET)" if insert_type_str.endswith("UnsetType]") else ""
                )
                insert_property_strs.append(
                    f"{prop.name}: {insert_type_str}{default_value_str}"
                )
            # for update type
            if not prop.is_computed and not prop.readonly:
                patch_edgedb_conversion_map[prop.name] = FieldInfo(
                    cast=conversion_type,
                    base_cast=base_conversion_type,
                    cardinality=prop.cardinality,
                    readonly=prop.readonly,
                    required=prop.required,
                )
                patch_type_str = type_str
                if prop.required and prop.default:
                    patch_type_str = f"T.Optional[{patch_type_str}]"
                final_patch_type_str = f"T.Union[{patch_type_str}, UnsetType]"
                patch_property_strs.append(
                    f"{prop.name}: {final_patch_type_str} = Field(UNSET)"
                )

    link_function_strs: T.List[str] = []
    resolver_function_strs: T.List[str] = []
    updatable_links: T.Set[str] = set()
    exclusive_links: T.Set[str] = set()
    link_conversion_map: CONVERSION_MAP = {}
    edge_resolver_map: T.Dict[str, str] = {}

    for link in object_type.links:
        if link.name == "__type__":
            continue
        link_conversion_map[link.name] = FieldInfo(
            cast=link.target.model_name,
            base_cast=None,
            cardinality=link.cardinality,
            readonly=link.readonly,
            required=link.required,
        )
        edge_resolver_map[link.name] = f"{link.target.model_name}Resolver"
        if link.cardinality == Cardinality.Many:
            edge_resolver_map[
                link.name + COUNT_POSTFIX
            ] = f"{link.target.model_name}Resolver"
        if not link.readonly and not link.is_computed:
            updatable_links.add(link.name)
        if link.is_exclusive:
            exclusive_links.add(link.name)
        link_function_strs.append(build_node_link_function_str(link))
        resolver_function_strs.append(
            build_resolver_link_function_str(
                node_resolver_name=node_resolver_name, link=link
            )
        )
        # for insert
        if not link.is_computed and not link.not_insertable:
            insert_resolver_str = f"{link.target.model_name}Resolver"
            if (not link.required) or (link.required and link.default):
                insert_resolver_str = f"T.Optional[{insert_resolver_str}]"
            default_value_str = (
                " = None" if insert_resolver_str.startswith("T.Optional[") else ""
            )
            insert_property_strs.append(
                f"{link.name}: {insert_resolver_str}{default_value_str}"
            )
        # for update
        if not link.is_computed and not link.readonly:
            patch_resolver_str = f"{link.target.model_name}Resolver"
            if (not link.required) or (link.required and link.default):
                patch_resolver_str = f"T.Optional[{patch_resolver_str}]"
            final_patch_resolver_str = f"T.Union[{patch_resolver_str}, UnsetType]"
            patch_property_strs.append(
                f"{link.name}: {final_patch_resolver_str} = Field(default_factory=UnsetType)"
            )

    basemodel_properties = (
        [] if not node_config else node_config.basemodel_properties.keys()
    )
    custom_annotations = (
        [] if not node_config else node_config.custom_annotations.keys()
    )
    mutate_on_update = {} if not node_config else node_config.mutate_on_update

    orm_config_str = build_orm_config(
        model_name=object_type.node_name,
        updatable_fields={*updatable_fields, *updatable_links},
        exclusive_fields={*exclusive_fields, *exclusive_links},
        appendix_properties=appendix_properties,
        computed_properties=computed_properties,
        basemodel_properties=basemodel_properties,
        custom_annotations=custom_annotations,
        mutate_on_update=mutate_on_update,
        node_edgedb_conversion_map=node_edgedb_conversion_map,
        insert_edgedb_conversion_map=insert_edgedb_conversion_map,
        patch_edgedb_conversion_map=patch_edgedb_conversion_map,
        insert_link_conversion_map=link_conversion_map,
    )

    insert_model_name = f"{object_type.node_name}Insert"
    patch_model_name = f"{object_type.node_name}Patch"

    # insert type
    insert_conversion_map_str = f"_edgedb_conversion_map: T.Dict[str, T.Dict[str, T.Union[str, bool]]] = {stringify_dict(insert_edgedb_conversion_map)}"
    insert_s = insert_patch_str(
        is_hydrated=insert_hydrate,
        property_strs=insert_property_strs,
        model_name=insert_model_name,
        insert_patch=InsertPatch.INSERT,
    )

    # patch type
    patch_conversion_map_str = f"_edgedb_conversion_map: T.Dict[str, T.Dict[str, T.Union[str, bool]]] = {stringify_dict(patch_edgedb_conversion_map)}"
    patch_s = insert_patch_str(
        is_hydrated=patch_hydrate,
        property_strs=patch_property_strs,
        model_name=patch_model_name,
        insert_patch=InsertPatch.PATCH,
    )

    # node
    node_properties_str = "\n".join(property_strs)
    from_str_validator_str = build_from_str_validator_str(node_config=node_config)
    if hydrate:
        node_properties_str = ""
        from_str_validator_str = ""

    computed_property_getter_str = "\n".join(computed_property_getter_strs)
    node_conversion_map_str = f"_edgedb_conversion_map: T.Dict[str, T.Dict[str, T.Union[str, bool]]] = {stringify_dict(node_edgedb_conversion_map)}"
    insert_link_conversion_map_str = f"_link_conversion_map: T.Dict[str, T.Dict[str, T.Union[str, bool]]] = {stringify_dict(link_conversion_map)}"
    computed_properties_str = f"_computed_properties: T.ClassVar[T.Set[str]] = {stringify_set(computed_properties)}"
    appendix_properties_str = f"_appendix_properties: T.ClassVar[T.Set[str]] = {stringify_set(appendix_properties)}"

    basemodel_properties_str = f"_basemodel_properties: T.ClassVar[T.Set[str]] = {stringify_set(set(basemodel_properties))}"

    custom_annotations_str = f"_custom_annotations: T.ClassVar[T.Set[str]] = {stringify_set(set(custom_annotations))}"
    node_link_functions_str = "\n".join(link_function_strs)

    if dehydrate:
        node_link_functions_str = ""
    node_inner_strs = [
        node_properties_str,
        "\n",
        from_str_validator_str,
        "\n",
        computed_property_getter_str,
        # node_conversion_map_str,
        # insert_link_conversion_map_str,
        # computed_properties_str,
        # appendix_properties_str,
        # basemodel_properties_str,
        # custom_annotations_str,
        node_link_functions_str,
        orm_config_str,
    ]
    node_inner_str = "\n".join(remove_falsies(node_inner_strs))
    inherits = f"Node" if not hydrate else f"{object_type.node_name}Hydrated"
    node_s = (
        f"class {object_type.node_name}({inherits}):\n{indent_lines(node_inner_str)}"
    )

    # resolver
    clses = [
        f"_node_cls = {object_type.node_name}",
        f"_insert_cls = {object_type.node_name}Insert",
        f"_patch_cls = {object_type.node_name}Patch",
    ]
    resolver_properties_str = "\n".join(clses)
    resolver_link_functions_str = "\n".join(resolver_function_strs)
    resolver_get_functions_str = build_exclusive_functions_str(
        node_name=object_type.node_name, exclusive_field_names=exclusive_fields
    )
    resolver_include_fields_str = build_include_fields_function(
        node_resolver_name=node_resolver_name,
        appendix_properties=appendix_properties,
        computed_properties=computed_properties,
    )
    resolver_filter_functions_str = build_filter_functions_str(
        node_name=object_type.node_name, conversion_map=node_edgedb_conversion_map
    )

    edge_resolver_val_strs = [
        f"T.Type[{v}]" for v in sorted(set(edge_resolver_map.values()))
    ]

    union_type = (
        f"T.Union[{', '.join(edge_resolver_val_strs)}]"
        if edge_resolver_map
        else "T.Type[Resolver]"
    )
    edge_resolver_map_strs.append(
        f"{node_resolver_name}._edge_resolver_map: T.Dict[str, {union_type}] ="
        f" {stringify_dict(edge_resolver_map, stringify_value=False)}"
    )

    resolver_inner_strs = [
        resolver_properties_str,
        resolver_link_functions_str,
        resolver_get_functions_str,
        resolver_filter_functions_str,
        resolver_include_fields_str,
    ]
    resolver_inner_str = "\n".join(resolver_inner_strs)
    resolver_mixin_str = "" if not resolver_mixin_model else f", {resolver_mixin_model}"
    resolver_s = f"class {node_resolver_name}(Resolver[{object_type.node_name}, {insert_model_name}, {patch_model_name}]{resolver_mixin_str}):\n{indent_lines(resolver_inner_str)}"

    return f"{node_s}\n{insert_s}\n{patch_s}\n{resolver_s}"


async def build_nodes_and_resolvers(
    client: edgedb.AsyncIOClient,
    db_config: DBConfig,
    nodes_to_hydrate: T.Set[str],
    dehydrate: bool,
) -> str:
    object_types = await introspect_objects(client)
    node_strs: T.List[str] = []
    edge_resolver_map_strs: T.List[str] = []
    resolver_mixin_model = (
        None
        if not db_config.resolver_mixin_path
        else db_config.resolver_mixin_path.split(" ")[-1]
    )
    for object_type in object_types:
        node_strs.append(
            build_node_and_resolver(
                object_type,
                node_config=db_config.nodes.get(object_type.node_name),
                edge_resolver_map_strs=edge_resolver_map_strs,
                hydrate=object_type.node_name in nodes_to_hydrate and not dehydrate,
                insert_hydrate=object_type.node_name + "Insert" in nodes_to_hydrate
                and not dehydrate,
                patch_hydrate=object_type.node_name + "Patch" in nodes_to_hydrate
                and not dehydrate,
                dehydrate=dehydrate,
                resolver_mixin_model=resolver_mixin_model,
            )
        )
    update_forward_refs_inserts_str = "\n".join(
        [f"{o.node_name}Insert.update_forward_refs()" for o in object_types]
    )
    update_forward_refs_patches_str = "\n".join(
        [f"{o.node_name}Patch.update_forward_refs()" for o in object_types]
    )
    update_forward_refs_nodes_str = "\n".join(
        [f"{o.node_name}.update_forward_refs()" for o in object_types]
    )
    nodes_str = "\n".join(node_strs)
    edge_resolver_map_str = "\n".join(edge_resolver_map_strs)
    return f"{nodes_str}\n\n{update_forward_refs_inserts_str}\n\n{update_forward_refs_patches_str}\n\n{update_forward_refs_nodes_str}\n\n{edge_resolver_map_str}"


def add_quotes_to_non_env_vars(s: str) -> str:
    if re.fullmatch(ENV_VAR_PATTERN, s) is not None:
        return s
    return f'"{s}"'


def build_client(db_config: DBConfig) -> str:
    return f"CLIENT = create_async_client(dsn={db_config.dsn_str()})"


def validate_output_path(path: Path) -> None:
    if not os.path.isdir(path):
        if os.path.isfile(path):
            raise GeneratorException(
                f"output path {path=} must be a directory, not a file."
            )
        if not os.path.exists(path):
            os.makedirs(path)


def build_hydrate_imports(db_config: DBConfig) -> str:
    import_strs: T.List[str] = []
    for node_name, config in db_config.nodes.items():
        if config.module_path:
            hydrated_name = f"{node_name}Hydrated"
            import_strs.append(
                f"from {config.module_path} import {node_name} as {hydrated_name}"
            )
        if config.insert_path:
            insert_node_name = f"{node_name}Insert"
            insert_hydrated_name = f"{insert_node_name}Hydrated"
            import_strs.append(
                f"from {config.insert_path} import {insert_node_name} as {insert_hydrated_name}"
            )
        if config.patch_path:
            patch_node_name = f"{node_name}Patch"
            patch_hydrated_name = f"{patch_node_name}Hydrated"
            import_strs.append(
                f"from {config.patch_path} import {patch_node_name} as {patch_hydrated_name}"
            )
            # idk why i have the part below, was just copying from dgraph_orm, seems unecessary and wrong
            # import_strs.append(
            #     f"{hydrated_name}.{CONFIG_NAME}.resolver._node = {hydrated_name}"
            # )
    return "\n".join(import_strs)


def get_nodes_to_hydrate(db_config: DBConfig) -> T.Set[str]:
    node_names: T.Set[str] = set()
    for node_name, config in db_config.nodes.items():
        if config.module_path:
            node_names.add(node_name)
        if config.insert_path:
            node_names.add(node_name + "Insert")
        if config.patch_path:
            node_names.add(node_name + "Patch")
    return node_names


async def build_enums_from_config(db_config: DBConfig, include_strawberry: bool) -> str:
    client = edgedb.create_async_client(dsn=db_config.dsn)
    enums_imports = build_enum_imports()
    enums_str = await build_enums(client, include_strawberry=include_strawberry)
    s = "\n".join([enums_imports, enums_str])
    if s.strip().endswith(":"):
        s += " pass"
    s = format_str(s, mode=FileMode())
    return s


async def build_from_config(
    db_config: DBConfig,
    enums_module: str,
    hydrate: bool = False,
    dehydrate: bool = False,
) -> str:
    client = edgedb.create_async_client(dsn=db_config.dsn)
    imports_str = imports(
        enums_module=enums_module, resolver_mixin_path=db_config.resolver_mixin_path
    )
    client_str = build_client(db_config)
    cache_only_str = f"CACHE_ONLY: bool = {db_config.cache_only}"
    validator_module_imports = build_validator_module_imports(db_config)
    hydrate_imports = "" if not hydrate else build_hydrate_imports(db_config)
    nodes_and_resolvers_str = await build_nodes_and_resolvers(
        client,
        db_config=db_config,
        nodes_to_hydrate=get_nodes_to_hydrate(db_config),
        dehydrate=dehydrate,
    )

    s = "\n".join(
        [
            imports_str,
            client_str,
            cache_only_str,
            validator_module_imports,
            hydrate_imports,
            nodes_and_resolvers_str,
        ]
    )
    s = format_str(s, mode=FileMode())
    return s


async def generate(
    *,
    config_path: Path = None,
    db_config_map: T.Dict[str, DBConfig] = None,
    output_path: Path,
    include_strawberry: bool = False,
) -> None:
    if config_path is not None and db_config_map is not None:
        raise GeneratorException(
            "Provide either a config_path or db_config_map, not both."
        )
    if config_path is not None:
        validate_output_path(output_path)
        all_config_json_str = open(config_path).read()
        all_config_d = parse_raw_as(T.Dict[str, DBConfig], all_config_json_str)
    elif db_config_map is not None:
        all_config_d = db_config_map
    else:
        raise GeneratorException("Provide either a config_path or a config_model_map.")
    for db_name, db_config in all_config_d.items():
        if db_config.copy_config:
            db_config_to_copy = all_config_d[db_config.copy_config]
            db_config.hydrate = db_config_to_copy.hydrate
            db_config.nodes = db_config_to_copy.nodes

        # first build enums folder
        enums_s = await build_enums_from_config(
            db_config=db_config, include_strawberry=include_strawberry
        )
        enums_module = f"{db_name}_enums"
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        open(output_path / f"{enums_module}.py", "w").write(enums_s)
        hydrate = db_config.hydrate
        # must include strawberry types in both for circular dependency reasons
        s = await build_from_config(
            db_config=db_config,
            dehydrate=hydrate,
            enums_module=enums_module,
        )
        open(output_path / f"{db_name}.py", "w").write(s)
        if hydrate:
            s = await build_from_config(
                db_config=db_config,
                hydrate=True,
                enums_module=enums_module,
            )
            open(output_path / f"{db_name}_hydrated.py", "w").write(s)
