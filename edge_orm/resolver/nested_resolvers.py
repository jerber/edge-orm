import typing as T
from pydantic import BaseModel


if T.TYPE_CHECKING:
    from .model import Resolver

ResolverType = T.TypeVar("ResolverType", bound="Resolver")  # type: ignore

SEPARATOR = "_*EDGE*_"


class NestedResolvers(BaseModel):
    d: dict[str, list[T.Any]] = {}

    def get(self, edge: str) -> list[ResolverType]:
        return self.d.get(edge, [])

    def has(self, edge: str) -> bool:
        return edge in self.d

    def add(
        self,
        edge: str,
        resolver: ResolverType,
        *,
        merge: bool = False,
        make_first: bool = False
    ) -> None:
        # TODO do merge... i guess worry about this later
        if not self.has(edge):
            self.d[edge] = []
        if make_first:
            self.d[edge].insert(0, resolver)
        else:
            self.d[edge].append(resolver)

    def has_subset(self, edge: str, resolver: ResolverType) -> bool:
        for r in self.get(edge):  # type: ignore
            if resolver.is_subset_of(r):
                return True
        return False

    def is_subset_of(self, other: "NestedResolvers") -> bool:
        for edge, resolvers in self.d.items():
            for r in resolvers:
                if not other.has_subset(edge=edge, resolver=r):
                    return False
        return True

    """
    def merge(self) -> "NestedResolvers":
        merged_nested_resolvers = NestedResolvers()
        for edge, resolvers in self.d.items():
            for r in resolvers:
                r.merge()
                merged_nested_resolvers.add(edge=edge, resolver=r, merge=True)
        return merged_nested_resolvers
    """
