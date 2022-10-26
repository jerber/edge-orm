from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from pydantic import BaseModel
from edge_orm import Resolver, Node, ResolverException, resolver_enums


class UserInsert(BaseModel):
    ...


class UserPatch(BaseModel):
    ...


# class User(Node[UserInsert, UserPatch]):
class User(Node):
    name: str
    age: int
    created_at: datetime

    class Edge:
        appendix_properties = {"created_at"}
        computed_properties = {"names_of_friends"}


class UserResolver(Resolver[User]):
    class Edge:
        node = User


def now() -> datetime:
    return datetime.now(tz=ZoneInfo("America/New_York"))


def test_simple_filter() -> None:
    rez = UserResolver()
    simple_filter = "exists .name"
    rez.filter(simple_filter)
    assert rez._filter == simple_filter


def test_filter_with_variables() -> None:
    rez = UserResolver()
    date_filter = f".created_at > <datetime>$now"
    d = now()
    rez.filter(date_filter, {"now": d})
    assert rez._filter == date_filter
    assert rez._query_variables == {"now": d}
    rez.filter(date_filter, {"now": d})
    with pytest.raises(ResolverException) as e:
        rez.filter(date_filter, {"now": now()})
    name = "Juan"
    rez.filter("name = <str>$name", {"name": name})
    assert rez._query_variables == {"now": d, "name": name}


def test_filters_str() -> None:
    rez = UserResolver()
    created_at_filter = f".created_at > <datetime>$ca"
    last_updated_at_filter = f".last_updated_at > <datetime>$la"
    rez.filter(created_at_filter, {"cs": now()})
    rez.filter(last_updated_at_filter, {"la": now()})
    with pytest.raises(ResolverException) as e:
        rez.filter(last_updated_at_filter, {"la": now()})
    print(f"{rez.build_filters_str()}")
    assert (
        rez.build_filters_str()
        == "FILTER "
        + resolver_enums.FilterConnector.AND.join(
            [created_at_filter, last_updated_at_filter]
        )
    )


def test_filters_str_with_order_by() -> None:
    rez = UserResolver()
    created_at_filter = f".created_at > <datetime>$ca"
    rez.filter(created_at_filter, {"ca": now()})
    order_by = ".created_at ASC"
    rez.order_by(order_by)
    assert (
        rez.build_filters_str()
        == "FILTER " + created_at_filter + " ORDER BY " + order_by
    )


def test_limit_offset_zeros() -> None:
    rez = UserResolver()
    rez.limit(0)
    with pytest.raises(ResolverException) as e:
        rez.limit(10)
    rez.offset(0)
    with pytest.raises(ResolverException) as e:
        rez.offset(10)
    assert rez.build_filters_str() == ""


def test_filters_str_with_all() -> None:
    rez = UserResolver()
    created_at_filter = f".created_at > <datetime>$ca"
    rez.filter(created_at_filter, {"ca": now()})
    order_by = ".created_at ASC"
    rez.order_by(order_by)
    limit = 30
    rez.limit(limit)
    with pytest.raises(ResolverException) as e:
        rez.limit(10)
    offset = 20
    rez.offset(offset)
    with pytest.raises(ResolverException) as e:
        rez.offset(10)

    assert (
        rez.build_filters_str()
        == "FILTER "
        + created_at_filter
        + " ORDER BY "
        + order_by
        + f" OFFSET {offset} LIMIT {limit}"
    )


"""TEST RETURN FIELDS"""


def test_fields_to_return() -> None:
    rez = UserResolver()
    assert rez._fields_to_return == {"id", "name", "age"}
    rez.include_fields("created_at")
    assert rez._fields_to_return == {"id", "name", "age", "created_at"}
    rez.exclude_fields("age", "created_at")
    assert rez._fields_to_return == {"id", "name"}
    rez.include_computed_properties()
    assert rez._fields_to_return == {"id", "name", "names_of_friends"}
    rez.include_appendix_properties()
    assert rez._fields_to_return == {"id", "name", "names_of_friends", "created_at"}
    extra_field_1 = ["friends_names := .friends.name", "friends_ids := .friends.ids"]
    rez.extra_field("friends_names", ".friends.name")
    rez.extra_field("friends_ids", ".friends.ids", conversion_func=UUID)
    assert rez._extra_fields == {*extra_field_1}
    assert rez._extra_fields_conversion_funcs["friends_ids"] == UUID
    extra_field_2 = "friends_fb_ids := .friends.auth_id"
    rez.extra_field("friends_fb_ids", ".friends.auth_id")
    assert rez._extra_fields == {*extra_field_1, extra_field_2}
    assert (
        rez.build_return_fields_str()
        == "created_at, friends_fb_ids := .friends.auth_id, friends_ids := .friends.ids, friends_names := .friends.name, id, name, names_of_friends"
    )
