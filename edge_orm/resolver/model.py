import typing as T
from pydantic import BaseModel, PrivateAttr
from edge_orm.node import Node
from . import enums, errors

NodeType = T.TypeVar("NodeType", bound=Node)
EdgeNodeType = T.TypeVar("EdgeNodeType", bound=T.Type[Node])
ThisResolverType = T.TypeVar("ThisResolverType", bound="Resolver")  # type: ignore

VARS = dict[str, T.Any]


class Resolver(BaseModel, T.Generic[NodeType]):
    _filter: str = PrivateAttr(None)
    _order_by: str = PrivateAttr(None)
    _limit: int = PrivateAttr(None)
    _offset: int = PrivateAttr(None)

    _query_variables: VARS = PrivateAttr(default_factory=dict)

    _fields_to_return: set[str] = PrivateAttr(None)  # init this?

    def __init__(self, **data: T.Any) -> None:
        super().__init__(**data)
        if self._fields_to_return is None:
            self._fields_to_return = (
                self.node_field_names() - self.node_appendix_properties()
            )

    class Edge(T.Generic[EdgeNodeType]):
        node: T.Type[EdgeNodeType]

    @classmethod
    def node_cls(cls) -> T.Type[NodeType]:
        return cls.Edge.node  # type: ignore

    @classmethod
    def node_field_names(cls: T.Type[ThisResolverType]) -> set[str]:
        return {field.alias for field in cls.node_cls().__fields__.values()}

    @classmethod
    def node_appendix_properties(cls) -> set[str]:
        return cls.node_cls().Edge.appendix_properties

    @classmethod
    def node_computed_properties(cls) -> set[str]:
        return cls.node_cls().Edge.computed_properties

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

    def build_filters_str(self) -> str:
        s_lst = [
            self._filter_str(),
            self._order_by_str(),
            self._offset_str(),
            self._limit_str(),
        ]
        s = " ".join([s for s in s_lst if s])
        return s

    def return_fields_str(self) -> str:
        ...

    def query_str(self) -> str:
        # there's the innter parts and the outer parts
        # select User{id, name, phone_number} filter .name = "hane"
        ...

    """QUERY METHODS"""

    def query(self) -> T.List[NodeType]:
        # TODO
        # DOCS
        ...

    def query_one(self) -> NodeType:
        # TODO
        # DOCS
        ...
