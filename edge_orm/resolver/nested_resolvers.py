import typing as T
from pydantic import BaseModel
from edge_orm import helpers
from edge_orm.types_generator.main import COUNT_POSTFIX

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
        from .merging import merge_resolvers

        if not self.has(edge):
            self.d[edge] = []

        if merge:
            existing_resolvers: list[ResolverType] = self.get(edge)
            new_resolvers: list[ResolverType] = []
            has_merged = False
            for existing_r in existing_resolvers:
                if has_merged is False and (
                    merged_r := merge_resolvers(resolver, existing_r)
                ):
                    new_resolvers.append(merged_r)
                    has_merged = True
                else:
                    new_resolvers.append(existing_r)
            self.d[edge] = new_resolvers
            if has_merged is True:
                return

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

    def edge_to_query_str_and_vars(self, edge: str, prefix: str) -> tuple[str, "VARS"]:
        resolvers: list["Resolver"] = self.get(edge)
        resolvers_str = []
        vars_lst = []
        for i, r in enumerate(resolvers):
            if i == 0:
                new_prefix = f"{prefix}{helpers.SEPARATOR}{edge}" if prefix else edge
                if r.is_count and COUNT_POSTFIX in edge:
                    # avoid not copying resolver and having it break. make SURE it is a count
                    filters_str, variables = r.build_filters_str_and_vars(
                        prefix=new_prefix
                    )
                    resolver_s = f"{edge} := count((SELECT .{edge.split(COUNT_POSTFIX)[0]} {filters_str}))"
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
                if r.is_count and COUNT_POSTFIX in edge:
                    filters_str, variables = r.build_filters_str_and_vars(
                        prefix=new_prefix
                    )
                    resolver_s = f"{key_name} := count((SELECT .{edge.split(COUNT_POSTFIX)[0]} {filters_str}))"
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
        edge_strs.sort()
        s = ", ".join(edge_strs)
        flattened_d = {k: v for d in vars_lst for k, v in d.items()}
        return s, flattened_d

    def resolver_from_field_name(self, field_name: str) -> ResolverType | None:
        possible_edge = field_name.split(helpers.SEPARATOR)[0]
        resolvers: list[ResolverType] = self.get(possible_edge)
        if not resolvers:
            return None
        if helpers.SEPARATOR not in field_name:
            return resolvers[0]
        try:
            index = int(field_name.split(helpers.SEPARATOR)[1])
            return resolvers[index]
        except (IndexError, ValueError):
            return None

    """MERGE"""

    def merge(self) -> "NestedResolvers":
        merged_nested_resolvers = NestedResolvers()
        for edge, resolvers in self.d.items():
            for r in resolvers:
                r.merge()
                merged_nested_resolvers.add(edge=edge, resolver=r, merge=True)
        return merged_nested_resolvers
