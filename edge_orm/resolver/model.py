# .query
# .query_str

# ability to add custom filters, filter by, etc... but this can all be added after...

# should store given: limit, order_by, offset, extra_fields_sts, filter_strs, update_operation

# is_subset

# start w no cache and build
import typing as T
from pydantic import BaseModel, PrivateAttr
from edge_orm.node import Node
from . import enums, errors

NodeType = T.TypeVar("NodeType", bound=Node)
ThisResolverType = T.TypeVar("ThisResolverType", bound="Resolver")

VARS = dict[str, T.Any]


class Resolver(BaseModel, T.Generic[NodeType]):
    _node: T.ClassVar[T.Type[NodeType]]

    _filter: str = PrivateAttr(None)
    _order_by: str = PrivateAttr(None)
    _limit: int = PrivateAttr(None)
    _offset: int

    _query_variables: VARS = PrivateAttr(default_factory=dict)

    def add_query_variables(self, variables: VARS) -> None:
        # can vars be enums now? Or should I do this later?
        # also do conflicting nested later
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
        # TODO document
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
