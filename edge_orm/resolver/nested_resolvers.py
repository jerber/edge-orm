import typing as T
from pydantic import BaseModel
from edge_orm import helpers

if T.TYPE_CHECKING:
    from .model import Resolver, VARS

ResolverType = T.TypeVar("ResolverType", bound="Resolver")


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

    def edge_to_query_str_and_vars(self, edge: str, prefix: str) -> tuple[str, "VARS"]:
        resolvers: list["Resolver"] = self.get(edge)
        resolvers_str = []
        vars_lst = []
        for i, r in enumerate(resolvers):
            if i == 0:
                new_prefix = f"{prefix}{helpers.SEPARATOR}{edge}" if prefix else edge
                if r.is_count and "__count" in edge:
                    # avoid not copying resolver and having it break. make SURE it is a count
                    filters_str, variables = r.build_filters_str_and_vars(
                        prefix=new_prefix
                    )
                    resolver_s = f'{edge} := COUNT((SELECT .{edge.split("__")[0]} {filters_str}))'
                else:
                    filters_str, variables = r.full_query_str_and_vars(
                        include_select=False, prefix=new_prefix
                    )
                    resolver_s = f"{edge}: {filters_str}"
            else:
                key_name = f"{edge}{helpers.SEPARATOR}{i}"
                new_prefix = (
                    f"{prefix}{helpers.SEPARATOR}{key_name}" if prefix else key_name
                )
                if r.is_count and "__count in edge":
                    filters_str, variables = r.build_filters_str_and_vars(
                        prefix=new_prefix
                    )
                    resolver_s = f"{key_name} := COUNT((SELECT .{edge.split('__')[0]} {filters_str}))"
                else:
                    filters_str, variables = r.full_query_str_and_vars(
                        include_select=False, prefix=new_prefix
                    )
                    resolver_s = f"{key_name} := (SELECT .{edge} {filters_str})"
            resolvers_str.append(resolver_s)
            vars_lst.append(variables)
        flattened_d = {k: v for d in vars_lst for k, v in d.items()}
        return ", ".join(resolvers_str), flattened_d

    def build_query_str_and_vars(self, prefix: str) -> tuple[str, "VARS"]:
        edge_strs: list[str] = []
        vars_lst: list["VARS"] = []
        keys = self.d.keys()
        for i, edge in enumerate(keys):
            s, v = self.edge_to_query_str_and_vars(edge=edge, prefix=prefix)
            edge_strs.append(s)
            vars_lst.append(v)

        s = ", ".join(edge_strs)
        flattened_d = {k: v for d in vars_lst for k, v in d.items()}
        return s, flattened_d
