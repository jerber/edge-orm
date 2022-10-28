import typing as T
import edgedb
from pydantic import BaseModel, PrivateAttr
from edge_orm.node import Node, Insert, Patch
from edge_orm.logs import logger
from edge_orm import helpers
from . import enums, errors
from .nested_resolvers import NestedResolvers
from devtools import debug

NodeType = T.TypeVar("NodeType", bound=Node)
InsertType = T.TypeVar("InsertType", bound=Insert)
PatchType = T.TypeVar("PatchType", bound=Patch)

EdgeNodeType = T.TypeVar("EdgeNodeType", bound=T.Type[Node])
ThisResolverType = T.TypeVar("ThisResolverType", bound="Resolver")  # type: ignore

VARS = dict[str, T.Any]
CONVERSION_FUNC = T.Callable[[str], T.Any]


class Resolver(BaseModel, T.Generic[NodeType, InsertType, PatchType]):
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

    is_count: bool = False

    def __init__(self, **data: T.Any) -> None:
        super().__init__(**data)
        if not self._fields_to_return:
            self._fields_to_return = (
                self.node_field_names()
                - self.node_appendix_properties()
                - self.node_computed_properties()
            )

    @classmethod
    def node_field_names(cls: T.Type[ThisResolverType]) -> set[str]:
        return {field.alias for field in cls._node_cls.__fields__.values()}

    @classmethod
    def node_appendix_properties(cls) -> set[str]:
        return cls._node_cls.EdgeConfig.appendix_properties

    @classmethod
    def node_computed_properties(cls) -> set[str]:
        return cls._node_cls.EdgeConfig.computed_properties

    """RESOLVER BUILDING METHODS"""

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

    def _filter_by(
        self: ThisResolverType,
        connector: enums.FilterConnector = enums.FilterConnector.AND,
        **kwargs: T.Any,
    ) -> ThisResolverType:
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if not kwargs:
            raise errors.ResolverException("Nothing to filter by.")
        conversion_map = self._node_cls.EdgeConfig.node_edgedb_conversion_map
        filter_strs = []
        variables = {}
        for field_name, field_value in kwargs.items():
            cast = conversion_map[field_name]["cast"]
            # variable_name = (
            #     f"{field_name}{helpers.random_str(10, include_re_code=True)}"
            # )
            variable_name = field_name
            filter_strs.append(f".{field_name} = <{cast}>${variable_name}")
            variables[variable_name] = field_value
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
        conversion_map = self._node_cls.EdgeConfig.node_edgedb_conversion_map
        filter_strs = []
        variables = {}
        for field_name, value_lst in kwargs.items():
            cast = conversion_map[field_name]["cast"]
            # variable_name = (
            #     f"{field_name}s{helpers.random_str(10, include_re_code=True)}"
            # )
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
        self._fields_to_return.update(self.node_appendix_properties())
        return self

    def include_computed_properties(self: ThisResolverType) -> ThisResolverType:
        self._fields_to_return.update(self.node_computed_properties())
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
        check_for_intersecting_variables: bool = False,
    ) -> tuple[str, VARS]:
        select = f"SELECT {self._node_cls.__name__} " if include_select else ""
        (
            nested_query_str,
            nested_vars,
        ) = self._nested_resolvers.build_query_str_and_vars(prefix=prefix)

        brackets_strs = [*self._fields_to_return, *self._extra_fields, nested_query_str]
        brackets_str = ", ".join(sorted([s for s in brackets_strs if s]))

        s = f"{select}{{ {brackets_str} }}"
        filters_str, query_vars = self.build_filters_str_and_vars(prefix=prefix)
        if filters_str:
            s += f" {filters_str}"

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

    def is_subset_of(self, other: "Resolver") -> bool:  # type: ignore
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
        # TODO merge
        query_str, variables = self.full_query_str_and_vars(
            include_select=True, prefix=""
        )
        # now what about vars
        print(query_str)
        from devtools import debug

        debug(variables)

        ...

    async def query_one(self) -> NodeType:
        # TODO
        # DOCS
        ...

    async def _get(
        self, *, client: edgedb.AsyncIOClient | None = None, **kwargs: T.Any
    ) -> NodeType | None:
        # TODO
        ...

    async def _gerror(
        self, *, client: edgedb.AsyncIOClient | None = None, **kwargs: T.Any
    ) -> NodeType:
        # TODO
        ...

    """MUTATION METHODS"""

    async def insert_one(
        self, insert: InsertType, *, client: edgedb.AsyncIOClient | None = None
    ) -> NodeType:
        # TODO
        ...

    async def insert_many(
        self, inserts: list[InsertType], *, client: edgedb.AsyncIOClient | None = None
    ) -> list[NodeType]:
        # TODO
        ...

    async def update_one(
        self, patch: PatchType, *, client: edgedb.AsyncIOClient | None = None
    ) -> NodeType:
        # TODO
        ...

    async def update_many(
        self, patch: PatchType, *, client: edgedb.AsyncIOClient | None = None
    ) -> list[NodeType]:
        # TODO
        ...
