import typing as T
import time
from pydantic import BaseModel
from edge_orm.unset import UNSET, UnsetType

if T.TYPE_CHECKING:
    from edge_orm.node.models import Node
    from edge_orm.resolver.model import Resolver

RAW = dict[str, T.Any] | list[dict[str, T.Any]]


class CacheException(Exception):
    pass


class CacheNode(BaseModel):
    # val: T.Union["Node", list["Node"]]
    val: T.Any  # this could be a count or a string or a bool...
    # resolver: "Resolver"  # type: ignore
    resolver: T.Any  # unfortunately circular ^
    timestamp: float


class Cache(BaseModel):
    d: dict[str, list[CacheNode]] = {}

    def get(self, edge: str) -> list[CacheNode]:
        return self.d.get(edge, [])

    def has(self, edge: str) -> bool:
        return edge in self.d

    def add(self, edge: str, resolver: "Resolver", val: T.Any) -> None:  # type: ignore
        if not self.has(edge):
            self.d[edge] = []
        self.d[edge].append(
            CacheNode(resolver=resolver, val=val, timestamp=time.time())
        )

    def clear(self, edge: str) -> None:
        if edge in self.d:
            del self.d[edge]

    def is_empty(self) -> bool:
        return bool(self.d)

    def val(self, edge: str, resolver: "Resolver") -> T.Any:  # type: ignore
        for node in self.get(edge):
            if resolver.is_subset_of(node.resolver):
                return node.val
        raise CacheException(
            f"No node with edge {edge}, resolver {resolver.__dict__} found."
        )

    def val_or_unset(self, edge: str, resolver: "Resolver") -> T.Any:  # type: ignore
        try:
            return self.val(edge=edge, resolver=resolver)
        except CacheException:
            return UNSET
