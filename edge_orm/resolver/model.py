import typing as T
import json
import re
import edgedb
from pydantic import BaseModel, PrivateAttr
from pydantic.main import ModelMetaclass
from edge_orm.node import Node, Insert, Patch, EdgeConfigBase
from edge_orm.logs import logger
from edge_orm.external import encoders
from edge_orm import helpers, execute, span
from . import enums, errors, utils
from .nested_resolvers import NestedResolvers
from devtools import debug
from .merging import merge_nested_resolver

NodeType = T.TypeVar("NodeType", bound=Node)
InsertType = T.TypeVar("InsertType", bound=Insert)
PatchType = T.TypeVar("PatchType", bound=Patch)

EdgeNodeType = T.TypeVar("EdgeNodeType", bound=T.Type[Node])
ThisResolverType = T.TypeVar("ThisResolverType", bound="Resolver")  # type: ignore

VARS = dict[str, T.Any]
CONVERSION_FUNC = T.Callable[[str], T.Any]
FILTER_FIELDS = ["_filter", "_limit", "_offset", "_order_by"]
RAW_RESP_ONE = dict[str, T.Any]
RAW_RESP_MANY = list[RAW_RESP_ONE]
RAW_RESPONSE = RAW_RESP_ONE | RAW_RESP_MANY


class Meta(ModelMetaclass):
    """adds property _node_config to resolver from _node_cls"""

    def __new__(mcs, name, bases, dct, **kwargs):  # type: ignore
        x = super().__new__(mcs, name, bases, dct, **kwargs)
        if "_node_cls" in dct:
            x._node_config: EdgeConfigBase = dct["_node_cls"].EdgeConfig  # type: ignore
        return x


class Resolver(BaseModel, T.Generic[NodeType, InsertType, PatchType], metaclass=Meta):
    _filter: str = PrivateAttr(None)
    _order_by: str = PrivateAttr(None)
    _limit: int = PrivateAttr(None)
    _offset: int = PrivateAttr(None)

    _query_variables: VARS = PrivateAttr(default_factory=dict)

    _fields_to_return: set[str] = PrivateAttr(default_factory=set)  # init this?
    _extra_fields: set[str] = PrivateAttr(default_factory=set)
    _extra_fields_conversion_funcs: dict[str, CONVERSION_FUNC] = PrivateAttr(
        default_factory=dict
    )

    _nested_resolvers: NestedResolvers = PrivateAttr(default_factory=NestedResolvers)

    _node_cls: T.ClassVar[T.Type[NodeType]]  # type: ignore
    _insert_cls: T.ClassVar[T.Type[InsertType]]  # type: ignore
    _patch_cls: T.ClassVar[T.Type[PatchType]]  # type: ignore

    _node_config: T.ClassVar[EdgeConfigBase]

    is_count: bool = False
    update_operation: enums.UpdateOperation | None = None
    _merged: bool = PrivateAttr(False)

    _edge_resolver_map: T.ClassVar[dict[str, T.Type["Resolver"]]]  # type: ignore

    def __init__(self, **data: T.Any) -> None:
        super().__init__(**data)
        if not self._fields_to_return:
            self._fields_to_return = (
                self.node_field_names()
                - self._node_config.appendix_properties
                - self._node_config.computed_properties
            )

    @property
    def model_name(self) -> str:
        return self._node_config.model_name

    @classmethod
    def node_field_names(cls: T.Type[ThisResolverType]) -> set[str]:
        return {field.alias for field in cls._node_cls.__fields__.values()}

    """RESOLVER BUILDING METHODS"""

    def set_update_operation(
        self: ThisResolverType,
        replace: bool = False,
        add: bool = False,
        remove: bool = False,
    ) -> ThisResolverType:
        if replace:
            self.update_operation = enums.UpdateOperation.REPLACE
        elif add:
            self.update_operation = enums.UpdateOperation.ADD
        elif remove:
            self.update_operation = enums.UpdateOperation.REMOVE
        else:
            raise errors.ResolverException("Invalid update operation given.")
        return self

    def add_query_variables(self, variables: VARS | None) -> None:
        """

        :param variables: a dictionary of query variables to smartly merge with _query_variables
        :return: None
        """
        # can vars be enums now? Or should I do this later?
        # also do conflict nested later
        if not variables:
            return
        for key, val in variables.items():
            if key in self._query_variables:
                if val is not self._query_variables[key]:
                    raise errors.ResolverException(
                        f"Variable {key}, {val=} is already used."
                    )
            self._query_variables[key] = val

    def filter(
        self: ThisResolverType,
        filter_str: str,
        variables: VARS | None = None,
        connector: enums.FilterConnector = enums.FilterConnector.AND,
    ) -> ThisResolverType:
        """

        :param filter_str: string to filter by, like .name = <str>$name
        :param variables: query variables from filter_str, like {"name": "Paul Graham"}
        :param connector: how to connect to an existing filter.
         If OR and (.name = <str>$name) was already set as the filter, the new filter would be:
         .name = <str>$name OR .slug = <str>$slug
        :return: the resolver
        """
        if self._filter and not connector:
            raise errors.ResolverException(
                f"Filter of {self._filter=} has already been provided so connector needed."
            )
        if not self._filter and connector is enums.FilterConnector.OR:
            raise errors.ResolverException(
                f"You cannot try to filter with OR while there is no existing filter."
            )
        self.add_query_variables(variables=variables)
        if self._filter:
            self._filter = f"{self._filter}{connector.value}{filter_str}"
        else:
            self._filter = filter_str
        return self

    def filter_str_from_field_name(self, field_name: str) -> str:
        cast = self._node_config.node_edgedb_conversion_map[field_name].cast
        return f".{field_name} = <{cast}>${field_name}"

    def _filter_by(
        self: ThisResolverType,
        connector: enums.FilterConnector = enums.FilterConnector.AND,
        **kwargs: T.Any,
    ) -> ThisResolverType:
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if not kwargs:
            raise errors.ResolverException("Nothing to filter by.")
        conversion_map = self._node_config.node_edgedb_conversion_map
        filter_strs = []
        variables = {}
        for field_name, field_value in kwargs.items():
            cast = conversion_map[field_name].cast
            filter_strs.append(f".{field_name} = <{cast}>${field_name}")
            variables[field_name] = field_value
        filter_str = " AND ".join(filter_strs)
        return self.filter(
            filter_str=filter_str, variables=variables, connector=connector
        )

    def _filter_in(
        self: ThisResolverType,
        connector: enums.FilterConnector = enums.FilterConnector.AND,
        **kwargs: T.Any,
    ) -> ThisResolverType:
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if not kwargs:
            raise errors.ResolverException("Nothing to filter by.")
        conversion_map = self._node_config.node_edgedb_conversion_map
        filter_strs = []
        variables = {}
        for field_name, value_lst in kwargs.items():
            cast = conversion_map[field_name].cast
            variable_name = field_name
            if cast.startswith("default::"):  # if an enum or other scalar
                s = f".{field_name} in <{cast}>array_unpack(<array<str>>${variable_name})"
            else:
                s = f".{field_name} in array_unpack(<array<{cast}>>${variable_name})"
            filter_strs.append(s)
            variables[variable_name] = value_lst
        filter_str = " AND ".join(filter_strs)
        return self.filter(
            filter_str=filter_str, variables=variables, connector=connector
        )

    def order_by(
        self: ThisResolverType,
        order_by_str: str,
        variables: VARS | None = None,
        then: bool = False,
    ) -> ThisResolverType:
        """

        :param order_by_str: string to order by, like .created_at ASC
        :param variables: query variables if used in the order_by_str
        :param then: allows you to append this order by if order by already exists
        :return: the resolver
        """
        if self._order_by and not then:
            raise errors.ResolverException(
                f"Order by of {self._order_by} has already been provided."
            )
        self.add_query_variables(variables)
        if self._order_by:
            self._order_by = f"{self._order_by} THEN {order_by_str}"
        else:
            self._order_by = order_by_str
        return self

    def offset(self: ThisResolverType, /, _: int | None) -> ThisResolverType:
        if self._offset is not None:
            raise errors.ResolverException(
                f"Offset of {self._offset} has already been provided."
            )
        self._offset = _
        return self

    def limit(self: ThisResolverType, /, _: int | None) -> ThisResolverType:
        if self._limit is not None:
            raise errors.ResolverException(
                f"Limit of {self._limit} has already been provided."
            )
        self._limit = _
        return self

    def include_fields(
        self: ThisResolverType, *fields_to_include: str
    ) -> ThisResolverType:
        self._fields_to_return.update(fields_to_include)
        return self

    def exclude_fields(
        self: ThisResolverType, *fields_to_exclude: str
    ) -> ThisResolverType:
        self._fields_to_return = self._fields_to_return - set(fields_to_exclude)
        return self

    def include_appendix_properties(self: ThisResolverType) -> ThisResolverType:
        self._fields_to_return.update(self._node_config.appendix_properties)
        return self

    def include_computed_properties(self: ThisResolverType) -> ThisResolverType:
        self._fields_to_return.update(self._node_config.computed_properties)
        return self

    def extra_field(
        self: ThisResolverType,
        field_name: str,
        expression: str,
        conversion_func: CONVERSION_FUNC | None = None,
    ) -> ThisResolverType:
        """extra fields do NOT take in variables"""
        extra_field_str = f"{field_name} := {expression}"
        self._extra_fields.add(extra_field_str)
        if conversion_func:
            self._extra_fields_conversion_funcs[field_name] = conversion_func
        return self

    """QUERY BUILDING METHODS"""

    def _filter_str(self) -> str:
        if not self._filter:
            return ""
        return f"FILTER {self._filter}"

    def _order_by_str(self) -> str:
        if not self._order_by:
            return ""
        return f"ORDER BY {self._order_by}"

    def _limit_str(self) -> str:
        if not self._limit or self._limit == 0:
            return ""
        return f"LIMIT {self._limit}"

    def _offset_str(self) -> str:
        if not self._offset or self._offset == 0:
            return ""
        return f"OFFSET {self._offset}"

    def build_filters_str_and_vars(self, prefix: str) -> tuple[str, VARS]:
        """Only returning the vars for THIS obj"""
        s_lst = [
            self._filter_str(),
            self._order_by_str(),
            self._offset_str(),
            self._limit_str(),
        ]
        s = " ".join([s for s in s_lst if s])
        if prefix:
            # regex out the vars to include this prefix
            new_prefix = f"{prefix}{helpers.SEPARATOR}"
            new_s = s.replace("$", f"${new_prefix}")
            new_vars = {f"{new_prefix}{k}": v for k, v in self._query_variables.items()}
            return new_s, new_vars
        else:
            return s, self._query_variables

    def full_query_str_and_vars(
        self,
        include_select: bool,
        prefix: str,
        include_filters: bool = True,
        include_detached: bool = False,
        check_for_intersecting_variables: bool = False,
        model_name_override: str = None,
    ) -> tuple[str, VARS]:
        self.merge()
        model_name = model_name_override or self.model_name
        detached_str = f" DETACHED" if include_detached else ""
        select = f"SELECT{detached_str} {model_name} " if include_select else ""
        (
            nested_query_str,
            nested_vars,
        ) = self._nested_resolvers.build_query_str_and_vars(prefix=prefix)
        brackets_strs = [
            *sorted(self._fields_to_return),
            *sorted(self._extra_fields),
            nested_query_str,
        ]
        brackets_str = ", ".join([s for s in brackets_strs if s])
        s = f"{select}{{ {brackets_str} }}"

        if include_filters:
            filters_str, query_vars = self.build_filters_str_and_vars(prefix=prefix)
            if filters_str:
                s += f" {filters_str}"
        else:
            query_vars = {}

        if check_for_intersecting_variables:
            # this is unlikely to happen because of the separator and prefix but just for sanity you can do this
            # if you do not have "__" in your variables this *is* impossible
            if inters := (query_vars.keys() & nested_vars.keys()):
                for var_name in inters:
                    if query_vars[var_name] != nested_vars[var_name]:
                        raise errors.ResolverException(
                            f"Variable {var_name} was given multiple times with different values: "
                            f"{query_vars[var_name]} != {nested_vars[var_name]}"
                        )

        return s, {**query_vars, **nested_vars}

    """MERGING LOGIC"""

    def build_hydrated_filters_str(self) -> str:
        filters_str, _ = self.build_filters_str_and_vars(prefix="")
        return helpers.replace_str_with_vars(
            s=filters_str, variables=self._query_variables
        )

    def is_subset_of(self, other: "Resolver", should_debug: bool = False) -> bool:  # type: ignore
        if self is other:
            return True
        if self._fields_to_return:
            self_additional_fields_to_return = (
                self._fields_to_return - other._fields_to_return
            )
            if self_additional_fields_to_return:
                logger.debug(f"{self_additional_fields_to_return=}")
                return False

        if self._extra_fields:
            self_additional_extra_fields = self._extra_fields - other._extra_fields
            if self_additional_extra_fields:
                logger.debug(f"{self_additional_extra_fields=}")
                return False
            self_additional_conversion_funcs = (
                self._extra_fields_conversion_funcs.keys()
                - other._extra_fields_conversion_funcs
            )
            if self_additional_conversion_funcs:
                logger.debug(f"{self_additional_conversion_funcs=}")
                return False

        # compare filter strs then variables then nested
        for key, val in self._query_variables.items():
            if key not in other._query_variables:
                logger.debug(f"{key} not in other._query_variables")
                return False
            if other._query_variables[key] != val:
                logger.debug(f"{other._query_variables[key]=} != {val=}")
                return False

        # PROs of this... it should be very safe since you are comparing the actual VARS
        # cons, it could be overly restrictive. If one is called $start_time vs $startTime it will break...fine tho
        self_filters_str, _ = self.build_filters_str_and_vars(prefix="")
        other_filters_str, _ = other.build_filters_str_and_vars(prefix="")
        if self_filters_str != other_filters_str:
            if should_debug:
                logger.debug(
                    f"{self.__class__.__name__}: {self_filters_str=} != {other_filters_str}"
                )
            return False

        if not self._nested_resolvers.is_subset_of(other._nested_resolvers):
            logger.debug(
                f"self nested_resolvers are not subset of other nested_resolvers"
            )
            return False

        return True

    """QUERY METHODS"""

    async def query(
        self, client: edgedb.AsyncIOClient | None = None
    ) -> T.List[NodeType]:
        query_str, variables = self.full_query_str_and_vars(
            include_select=True, prefix=""
        )
        with span.span(
            op=f"edgedb.query.{self.model_name}", description=query_str[:200]
        ):
            raw_response = await execute.query(
                client=client or self._node_config.client,
                query_str=query_str,
                variables=variables,
                only_one=False,
            )
        if not isinstance(raw_response, list):
            raise errors.ResolverException(
                f"Expected a list from query, got {raw_response}."
            )
        return self.parse_obj_with_cache_list(raw_response)

    async def query_first(
        self, client: edgedb.AsyncIOClient | None = None
    ) -> NodeType | None:
        if self._limit is not None and self._limit > 1:
            raise errors.ResolverException(
                f"Limit is set to {self._limit} so you cannot query_first."
            )
        self._limit = 1
        model_lst = await self.query(client=client)
        if not model_lst:
            return None
        return model_lst[0]

    async def count(self, client: edgedb.AsyncIOClient | None = None) -> int:
        query_str, variables = self.full_query_str_and_vars(
            include_select=False, prefix=""
        )

        query_str = f"SELECT count({self.model_name} {query_str})"
        with span.span(
            op=f"edgedb.query.{self.model_name}", description=query_str[:200]
        ):
            c = await execute.query(
                client=client or self._node_config.client,
                query_str=query_str,
                variables=variables,
                only_one=True,
            )
            if not isinstance(c, int):
                raise errors.ResolverException(f"Count must be an int {c=}.")
            return c

    async def _get(
        self,
        field_name: str,
        value: T.Any,
        *,
        client: edgedb.AsyncIOClient | None = None,
    ) -> NodeType | None:
        self.validate_field_name_value_filters(
            operation_name="get", field_name=field_name, value=value
        )
        query_str, variables = self.full_query_str_and_vars(
            include_select=True, prefix=""
        )
        custom_filter_str = f"FILTER {self.filter_str_from_field_name(field_name)}"
        query_str += f" {custom_filter_str}"
        with span.span(op=f"edgedb.get.{self.model_name}", description=query_str[:200]):
            raw_response = await execute.query(
                client=client or self._node_config.client,
                query_str=query_str,
                variables={**variables, field_name: value},
                only_one=True,
            )

        if not raw_response:
            return None
        return self.parse_obj_with_cache(raw_response)

    async def _gerror(
        self,
        field_name: str,
        value: T.Any,
        *,
        client: edgedb.AsyncIOClient | None = None,
    ) -> NodeType:
        model = await self._get(field_name=field_name, value=value, client=client)
        if not model:
            raise errors.ResolverException(
                f"No {self.model_name} in db with fields {field_name} = {value}."
            )
        return model

    """MUTATION METHODS"""

    @staticmethod
    def validate_upsert_fields(
        upsert_given_conflict_on: str = None,
        return_model_for_conflict_on: str = None,
        custom_conflict_on_str: str = None,
    ) -> None:
        if custom_conflict_on_str:
            if return_model_for_conflict_on or upsert_given_conflict_on:
                raise errors.ResolverException(
                    "You cannot give a custom conflict string with other conflict inputs."
                )
        if return_model_for_conflict_on and upsert_given_conflict_on:
            raise errors.ResolverException(
                "You cannot both suppress a conflict and upsert given a conflict."
            )

    def build_conflict_str_and_vars(
        self,
        insert: InsertType,
        *,
        mutate_on_update: bool,
        custom_conflict_on_str: str | None,
        upsert_given_conflict_on: str | None,
        return_model_for_conflict_on: str | None,
    ) -> tuple[str, VARS]:
        self.validate_upsert_fields(
            upsert_given_conflict_on=upsert_given_conflict_on,
            return_model_for_conflict_on=return_model_for_conflict_on,
            custom_conflict_on_str=custom_conflict_on_str,
        )

        conflict_str = ""
        conflict_variables: VARS = {}

        if custom_conflict_on_str:
            conflict_str = custom_conflict_on_str
        elif upsert_given_conflict_on:
            patch = self.patch_from_insert(insert)
            conflict_s, conflict_variables = utils.model_to_set_str_vars(
                model=patch,
                conversion_map=self._node_config.patch_edgedb_conversion_map,
                additional_link_str=self.build_mutate_on_update_str(
                    patch=patch, mutate_on_update=mutate_on_update
                ),
            )
            conflict_str = f"UNLESS CONFLICT ON .{upsert_given_conflict_on} else (UPDATE {self.model_name} SET {conflict_s})"
        elif return_model_for_conflict_on:
            conflict_str = f"UNLESS CONFLICT ON .{return_model_for_conflict_on} ELSE (SELECT {self.model_name})"

        return conflict_str, conflict_variables

    async def insert_one(
        self,
        insert: InsertType,
        *,
        client: edgedb.AsyncIOClient | None = None,
        upsert_given_conflict_on: str = None,
        custom_conflict_on_str: str = None,
        return_model_for_conflict_on: str = None,
        mutate_on_update: bool = True,
    ) -> NodeType:
        if existing_filter_str := self.has_filters():
            raise errors.ResolverException(
                f"This resolver already has filters: {existing_filter_str}. "
                f"If you wish to INSERT an object, use a resolver that does not have root filters."
            )
        insert_s, insert_variables = utils.model_to_set_str_vars(
            model=insert, conversion_map=self._node_config.insert_edgedb_conversion_map
        )
        insert_s = f"INSERT {self.model_name} {insert_s}"

        conflict_str, conflict_variables = self.build_conflict_str_and_vars(
            insert=insert,
            upsert_given_conflict_on=upsert_given_conflict_on,
            custom_conflict_on_str=custom_conflict_on_str,
            return_model_for_conflict_on=return_model_for_conflict_on,
            mutate_on_update=mutate_on_update,
        )
        if conflict_str:
            insert_s += f" {conflict_str}"

        # do not need the prefix since any var HAS to be nested, so will already have prefixes
        select_s, select_variables = self.full_query_str_and_vars(
            prefix="", model_name_override="model", include_select=True
        )
        final_insert_s = f"WITH model := ({insert_s}) {select_s}"
        with span.span(op=f"edgedb.add.{self.model_name}"):
            raw_response = await execute.query(
                client=client or self._node_config.client,
                query_str=final_insert_s,
                variables={
                    **select_variables,
                    **insert_variables,
                    **conflict_variables,
                },
                only_one=True,
            )
        raw_response = T.cast(RAW_RESP_ONE, raw_response)
        return self.parse_obj_with_cache(raw_response)

    async def insert_many(
        self, inserts: list[InsertType], *, client: edgedb.AsyncIOClient | None = None
    ) -> list[NodeType]:
        if not inserts:
            return []
        conversion_map = self._node_config.insert_edgedb_conversion_map
        first_insert_s, _ = utils.model_to_set_str_vars(
            model=inserts[0], conversion_map=conversion_map, json_get_item="item"
        )
        insert_vars_list: list[VARS] = []
        for insert in inserts:
            # confirm that the INSERT STRS of all of these are the same
            insert_s, insert_vars = utils.model_to_set_str_vars(
                model=insert, conversion_map=conversion_map, json_get_item="item"
            )
            if insert_s != first_insert_s:
                raise errors.ResolverException(
                    f"Not all inserts have the same form: {insert_s} != {first_insert_s}."
                )
            insert_vars_list.append(insert_vars)

        insert_s = f"INSERT {self.model_name} {first_insert_s}"
        select_s, select_variables = self.full_query_str_and_vars(
            prefix="", model_name_override="model", include_select=False
        )

        # for insert_s, replace $x with json_get(item, "x")
        insert_s = re.sub(
            pattern=r"\$(\w+)", repl='json_get(item, "' + r"\1" + '")', string=insert_s
        )

        final_insert_str = f"""
        with
            raw_data := <json>$__data,
        for item in json_array_unpack(raw_data) union ({insert_s}) {select_s}
                """
        variables = {
            **select_variables,
            "__data": json.dumps(encoders.jsonable_encoder(insert_vars_list)),
        }
        debug(variables)
        with span.span(op=f"edgedb.add_many.{self.model_name}"):
            raw_response = await execute.query(
                client=client or self._node_config.client,
                query_str=final_insert_str,
                variables=variables,
                only_one=False,
            )
        raw_response = T.cast(RAW_RESP_MANY, raw_response)
        return self.parse_obj_with_cache_list(raw_response)

    def build_mutate_on_update_str(
        self, patch: PatchType, mutate_on_update: bool | None
    ) -> str | None:
        if mutate_on_update is False:
            return None
        mutate_on_update_d = self._node_config.mutate_on_update
        if not mutate_on_update_d:
            return None
        mutate_on_update_strs: list[str] = []
        for field_name, expression in mutate_on_update_d.items():
            if field_name not in patch.set_fields_:
                mutate_on_update_strs.append(f"{field_name} := {expression}")
        mutate_on_update_str = ", ".join(mutate_on_update_strs)
        return mutate_on_update_str

    async def _update(
        self,
        patch: PatchType,
        *,
        field_name: str = None,
        value: T.Any = None,
        only_one: bool,
        mutate_on_update: bool,
        client: edgedb.AsyncIOClient | None,
    ) -> RAW_RESPONSE:
        update_s, update_variables = utils.model_to_set_str_vars(
            model=patch,
            conversion_map=self._node_config.patch_edgedb_conversion_map,
            additional_link_str=self.build_mutate_on_update_str(
                patch=patch, mutate_on_update=mutate_on_update
            ),
        )
        filters_s, filters_vars = self.build_filters_str_and_vars(prefix="")

        if only_one:
            if field_name is None:
                raise errors.ResolverException(
                    "Cannot be only_one and have no field_name."
                )
            custom_filter_str = f"FILTER {self.filter_str_from_field_name(field_name)}"
            filters_s += f" {custom_filter_str}"
            filters_vars[field_name] = value

        update_s = f"UPDATE {self.model_name} {filters_s} SET {update_s}"
        select_s, select_variables = self.full_query_str_and_vars(
            prefix="",
            model_name_override="model",
            include_select=True,
            include_filters=False,
        )
        final_update_s = f"WITH model := ({update_s}) {select_s}"
        with span.span(op=f"edgedb.update.{self.model_name}"):
            raw_response = await execute.query(
                client=client or self._node_config.client,
                query_str=final_update_s,
                variables={**select_variables, **filters_vars, **update_variables},
                only_one=only_one,
            )
        raw_response = T.cast(RAW_RESPONSE, raw_response)
        return raw_response

    def validate_field_name_value_filters(
        self, operation_name: str, field_name: str, value: T.Any
    ) -> None:
        if existing_filter_str := self.has_filters():
            raise errors.ResolverException(
                f"`{operation_name}` requires a resolver with *no* root filters but this resolver has root filters: "
                f"{existing_filter_str}. Instead, pass in the exclusive field + value "
                f"or use a resolver without root filters."
            )
        if value is None:
            raise errors.ResolverException("Value must not be None.")
        if field_name not in self._node_config.exclusive_fields:
            raise errors.ResolverException(f"Field '{field_name}' is not exclusive.")

    async def _update_one(
        self,
        patch: PatchType,
        *,
        field_name: str,
        value: T.Any,
        client: edgedb.AsyncIOClient | None = None,
        mutate_on_update: bool = True,
    ) -> NodeType:
        if not patch.set_fields_:
            raise errors.ResolverException("Patch is empty.")
        self.validate_field_name_value_filters(
            operation_name="update_one", field_name=field_name, value=value
        )
        raw_response = await self._update(
            patch=patch,
            field_name=field_name,
            value=value,
            only_one=True,
            client=client,
            mutate_on_update=mutate_on_update,
        )
        raw_response = T.cast(RAW_RESP_ONE, raw_response)
        if not raw_response:
            raise errors.ResolverException("No object to update.")
        return self.parse_obj_with_cache(raw_response)

    async def update_many(
        self,
        patch: PatchType,
        *,
        update_all: bool = False,
        client: edgedb.AsyncIOClient | None = None,
        mutate_on_update: bool = True,
    ) -> list[NodeType]:
        if not patch.set_fields_:
            raise errors.ResolverException("Patch is empty.")
        if not update_all:
            if not self.has_filters():
                raise errors.ResolverException(
                    "You did not give filters which means this will update *all* models. "
                    "If this is your intention, pass update_all=True."
                )
        raw_response = await self._update(
            patch=patch,
            only_one=False,
            client=client,
            mutate_on_update=mutate_on_update,
        )
        raw_response = T.cast(RAW_RESP_MANY, raw_response)
        return self.parse_obj_with_cache_list(raw_response)

    async def _delete(
        self,
        *,
        field_name: str = None,
        value: T.Any = None,
        only_one: bool,
        client: edgedb.AsyncIOClient | None,
    ) -> RAW_RESPONSE:
        filters_s, filters_vars = self.build_filters_str_and_vars(prefix="")

        if only_one:
            if field_name is None:
                raise errors.ResolverException(
                    "Cannot be only_one and have no field_name."
                )
            custom_filter_str = f"FILTER {self.filter_str_from_field_name(field_name)}"
            filters_s += f" {custom_filter_str}"
            filters_vars[field_name] = value

        delete_s = f"DELETE {self.model_name} {filters_s}"
        select_s, select_variables = self.full_query_str_and_vars(
            prefix="",
            model_name_override="model",
            include_select=True,
            include_filters=False,
        )
        final_delete_s = f"WITH model := ({delete_s}) {select_s}"
        with span.span(op=f"edgedb.delete.{self.model_name}"):
            raw_response = await execute.query(
                client=client or self._node_config.client,
                query_str=final_delete_s,
                variables={**select_variables, **filters_vars},
                only_one=only_one,
            )
        raw_response = T.cast(RAW_RESPONSE, raw_response)
        return raw_response

    async def _delete_one(
        self,
        *,
        field_name: str,
        value: T.Any,
        client: edgedb.AsyncIOClient | None = None,
    ) -> NodeType:
        self.validate_field_name_value_filters(
            operation_name="delete one", field_name=field_name, value=value
        )
        raw_response = await self._delete(
            field_name=field_name, value=value, only_one=True, client=client
        )
        raw_response = T.cast(RAW_RESP_ONE, raw_response)
        if not raw_response:
            raise errors.ResolverException("No object to delete.")
        return self.parse_obj_with_cache(raw_response)

    async def delete_many(
        self,
        *,
        delete_all: bool = False,
        client: edgedb.AsyncIOClient | None = None,
    ) -> list[NodeType]:
        if not delete_all:
            if not self.has_filters():
                raise errors.ResolverException(
                    "You did not give filters which means this will delete *all* models. "
                    "If this is your intention, pass delete_all=True."
                )
        raw_response = await self._delete(only_one=False, client=client)
        raw_response = T.cast(RAW_RESP_MANY, raw_response)
        return self.parse_obj_with_cache_list(raw_response)

    """HELPERS"""

    def has_filters(self) -> T.Optional[str]:
        for field in FILTER_FIELDS:
            if (val := getattr(self, field)) is not None:
                return val
        return None

    def patch_from_insert(self, insert: InsertType) -> PatchType:
        patch = self._patch_cls()
        for field in insert.set_fields_:
            if field in self._patch_cls.__fields__:
                setattr(patch, field, getattr(insert, field))
        return patch

    """PARSING"""

    def _parse_obj_with_cache(self, d: RAW_RESP_ONE) -> NodeType:
        # TODO counts will fail, catch counts early
        node = self._node_cls(**d)
        # TODO speed test
        fields_set = {re.sub(r"_$", "", s) for s in node.set_fields_}
        other_fields = d.keys() - fields_set
        for field_name in sorted(other_fields):
            resolver = self._nested_resolvers.resolver_from_field_name(field_name)
            if not resolver:
                # must be an extra field
                node.computed[field_name] = d[field_name]
            else:
                child = d[field_name]
                if child:
                    if isinstance(child, list):
                        val = [resolver._parse_obj_with_cache(d) for d in child]
                    elif isinstance(child, int):
                        # counts
                        val = child
                    else:
                        val = resolver._parse_obj_with_cache(child)
                else:
                    val = child
                edge_name = field_name.split(helpers.SEPARATOR)[0]
                node._cache.add(edge=edge_name, resolver=resolver, val=val)
        node._used_resolver = self
        return node

    def parse_obj_with_cache(self, d: RAW_RESP_ONE) -> NodeType:
        with span.span(op=f"parse.{self.model_name}"):
            return self._parse_obj_with_cache(d)

    def parse_obj_with_cache_list(self, lst: RAW_RESP_MANY) -> list[NodeType]:
        with span.span(op=f"parse_list.{self.model_name}", description=f"{len(lst)}"):
            return [self._parse_obj_with_cache(d) for d in lst]

    """merge"""

    def merge(self) -> None:
        self._nested_resolvers = merge_nested_resolver(self._nested_resolvers)
