# TODO copied from legacy so it is messy
import typing as T
from .nested_resolvers import NestedResolvers
from edge_orm import logger

if T.TYPE_CHECKING:
    from .model import Resolver

ResolverType = T.TypeVar("ResolverType", bound="Resolver")  # type: ignore


class MergeException(Exception):
    pass


def merge_fields(
    a: ResolverType,
    b: ResolverType,
    merged_resolver: ResolverType,
    key: str,
    separator: str = ", ",
) -> None:
    a_val = getattr(a, key, None)
    b_val = getattr(b, key, None)

    if a_val == b_val:
        setattr(merged_resolver, key, a_val)
    elif a_val is None or b_val is None:
        # one is None, so just use the other one's
        setattr(merged_resolver, key, a_val or b_val)
    else:
        # they both are not none and also not the same, hope there is no conflict!
        setattr(merged_resolver, key, f"{a_val}{separator}{b_val}")


def merge_resolvers(
    a: ResolverType, b: ResolverType, should_debug: bool = False
) -> T.Optional[ResolverType]:
    # first merge, then see if a and b are subsets. If they are, return! else, None, they can't be merged
    if a.__class__ != b.__class__:
        raise MergeException(
            f"Resolvers are not the same type, {a.__class__=}, {b.__class__=}"
        )
    merged_resolver = a.__class__()
    merged_resolver._merged = True

    # for these, filters must be the same anyway
    merged_resolver._filter = a._filter
    merged_resolver._order_by = a._order_by
    merged_resolver._limit = a._limit
    merged_resolver._offset = a._offset

    merge_fields(a, b, merged_resolver, key="_extra_fields")
    # merge_fields(a, b, merged_resolver, key="_modules")

    # can ignore update operation? -> yeah because these aren't used for updating
    merged_resolver._query_variables = {**a._query_variables, **b._query_variables}

    if a._fields_to_return is None and b._fields_to_return is None:
        merged_resolver._fields_to_return = None
    else:
        merged_resolver._fields_to_return = {
            *(a._fields_to_return or set()),
            *(b._fields_to_return or set()),
        }
    merged_resolver._fields_to_return = {*a._fields_to_return, *b._fields_to_return}

    merged_resolver._nested_resolvers = merge_nested_resolvers(
        a._nested_resolvers, b._nested_resolvers
    )

    # okay, now if subsets, return ! else None
    # or separate this??
    if a.is_subset_of(merged_resolver) and b.is_subset_of(merged_resolver):
        return merged_resolver
    if should_debug:
        logger.warning("NOT SUBSETS!")
        logger.warning(
            f"{a.is_subset_of(merged_resolver)=}, {b.is_subset_of(merged_resolver)=}"
        )
    return None


def merge_nested_resolvers(
    a: NestedResolvers, b: NestedResolvers
) -> T.Optional[NestedResolvers]:
    merged_nested_resolvers = NestedResolvers()
    all_edges = {*a.d.keys(), *b.d.keys()}

    for edge in all_edges:
        merged_resolvers: list[Resolver] = []  # type: ignore
        has_merged: list[Resolver] = []  # type: ignore

        a_resolvers: list[Resolver] = a.get(edge)  # type: ignore
        b_resolvers: list[Resolver] = b.get(edge)  # type: ignore
        for a_resolver in a_resolvers:
            if a_resolver in has_merged:
                continue
            for b_resolver in b_resolvers:
                if b_resolver in has_merged:
                    continue
                if merged_resolver := merge_resolvers(a_resolver, b_resolver):
                    merged_resolvers.append(merged_resolver)
                    # now mark these two resolvers as merged
                    has_merged.append(a_resolver)
                    has_merged.append(b_resolver)
        # do a second pass, all resolvers not merged add to resolver list
        for r in [*a_resolvers, *b_resolvers]:
            if r not in has_merged:
                merged_resolvers.append(r)

        # for r in merged_resolvers:
        #     merged_nested_resolvers.add(edge, resolver=r)
        if edge not in merged_nested_resolvers.d:
            merged_nested_resolvers.d[edge] = []
        merged_nested_resolvers.d[edge] = merged_resolvers

    return merged_nested_resolvers


def merge_resolvers_lst(resolvers: list[ResolverType]) -> list[ResolverType]:
    if not resolvers:
        return []
    q = resolvers.copy()
    merged: list[ResolverType] = []
    while q:
        new_q: list[ResolverType] = []
        main_r = q.pop()
        for other_r in q:
            if merged_r := merge_resolvers(main_r, other_r):
                main_r = merged_r
            else:
                new_q.append(other_r)
        merged.append(main_r)
        q = new_q
    return merged


def merge_nested_resolver(nested_resolvers: NestedResolvers) -> NestedResolvers:
    """
    merged_nested_resolvers = NestedResolvers()
    for edge, resolvers in nested_resolvers.d.items():
        merged_nested_resolvers.d[edge] = merge_resolvers_lst(resolvers)
    return merged_nested_resolvers
    """
    merged_nested_resolvers = NestedResolvers()
    for edge, resolvers in nested_resolvers.d.items():
        for r in resolvers:
            r.merge()
            merged_nested_resolvers.add(edge=edge, resolver=r, merge=True)
    return merged_nested_resolvers
