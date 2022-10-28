import typing as T
from pydantic import BaseModel


if T.TYPE_CHECKING:
    from .model import Resolver

ResolverType = T.TypeVar("ResolverType", bound="Resolver")

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
        make_first: bool = False,
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

    def edge_to_query_str(self, edge: str) -> str:
        resolvers: list["Resolver"] = self.get(edge)
        resolvers_str = []
        for i, r in enumerate(resolvers):
            if i == 0:
                if r.is_count and "__count" in edge:
                    # avoid not copying resolver and having it break. make SURE it is a count
                    resolver_s = f'{edge} := COUNT((SELECT .{edge.split("__")[0]} {r.build_filters_str()}))'
                else:
                    resolver_s = f"{edge}: {r.full_query_str(include_select=False)}"
            else:
                if r.is_count and "__count in edge":
                    resolver_s = f"{edge}{SEPARATOR}{i} := COUNT((SELECT .{edge.split('__')[0]} {r.build_filters_str()}))"
                else:
                    resolver_s = f"{edge}{SEPARATOR}{i} := (SELECT .{edge} {r.full_query_str(include_select=False)})"
            resolvers_str.append(resolver_s)
        return ", ".join(resolvers_str)

    def build_query_str(self) -> str:
        return ", ".join([self.edge_to_query_str(e) for e in self.d.keys()])
