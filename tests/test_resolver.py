from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from edge_orm import ResolverException, resolver_enums, logger
from tests.generator.gen import db_hydrated as db
import tests


logger.setLevel(0)


def now() -> datetime:
    return datetime.now(tz=ZoneInfo("America/New_York"))


def test_simple_filter() -> None:
    rez = db.UserResolver()
    simple_filter = "exists .name"
    rez.filter(simple_filter)
    assert rez._filter == simple_filter


def test_filter_with_variables() -> None:
    rez = db.UserResolver()
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
    rez = db.UserResolver()
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
    rez = db.UserResolver()
    created_at_filter = f".created_at > <datetime>$ca"
    rez.filter(created_at_filter, {"ca": now()})
    order_by = ".created_at ASC"
    rez.order_by(order_by)
    assert (
        rez.build_filters_str()
        == "FILTER " + created_at_filter + " ORDER BY " + order_by
    )


def test_limit_offset_zeros() -> None:
    rez = db.UserResolver()
    rez.limit(0)
    with pytest.raises(ResolverException) as e:
        rez.limit(10)
    rez.offset(0)
    with pytest.raises(ResolverException) as e:
        rez.offset(10)
    assert rez.build_filters_str() == ""


def test_filters_str_with_all() -> None:
    rez = db.UserResolver()
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
    rez = db.UserResolver()
    assert rez._fields_to_return == {"id", "name", "age", "phone_number"}
    rez.exclude_fields("phone_number")
    rez.include_fields("created_at")
    assert rez._fields_to_return == {"id", "name", "age", "created_at"}
    rez.exclude_fields("age", "created_at")
    assert rez._fields_to_return == {"id", "name"}
    rez.include_computed_properties()
    assert rez._fields_to_return == {"id", "name", "names_of_friends"}
    rez.include_appendix_properties()
    assert rez._fields_to_return == {
        "id",
        "name",
        "names_of_friends",
        "created_at",
        "last_updated_at",
    }
    extra_field_1 = ["friends_names := .friends.name", "friends_ids := .friends.ids"]
    rez.extra_field("friends_names", ".friends.name")
    rez.extra_field("friends_ids", ".friends.ids", conversion_func=UUID)
    assert rez._extra_fields == {*extra_field_1}
    assert rez._extra_fields_conversion_funcs["friends_ids"] == UUID
    extra_field_2 = "friends_fb_ids := .friends.auth_id"
    rez.extra_field("friends_fb_ids", ".friends.auth_id")
    assert rez._extra_fields == {*extra_field_1, extra_field_2}

    return_fields_str = "created_at, friends_fb_ids := .friends.auth_id, friends_ids := .friends.ids, friends_names := .friends.name, id, last_updated_at, name, names_of_friends"

    assert rez.build_return_fields_str() == return_fields_str
    rez.limit(20).filter("exists .friends")
    assert (
        rez.full_query_str(include_select=True)
        == f"SELECT User {{ {return_fields_str} }} FILTER exists .friends LIMIT 20"
    )


def test_subset() -> None:
    rez1 = db.UserResolver()
    rez2 = db.UserResolver().extra_field("hello", '<str>"hello"')
    assert rez1.is_subset_of(rez2) is True
    assert rez2.is_subset_of(rez1) is False

    rez1.extra_field("hello", '<str>"hello"')
    assert rez2.is_subset_of(rez1)

    rez1 = db.UserResolver().extra_field("hello", '<str>"hello"', conversion_func=UUID)
    assert rez1.is_subset_of(rez2) is False

    rez1 = db.UserResolver().extra_field("hello", '<str>"hello"', conversion_func=None)
    assert rez1.is_subset_of(rez2) is True

    rez1 = db.UserResolver().filter("exists .friends")
    rez2 = db.UserResolver().filter("exists .friends").limit(10)
    assert rez1.is_subset_of(rez2) is False
    assert rez2.is_subset_of(rez1) is False
    rez1.limit(10)
    assert rez1.is_subset_of(rez2)


def test_node_relationship() -> None:
    rez = db.UserResolver()
    assert "hi" not in rez._node_cls.EdgeConfig.appendix_properties


@pytest.mark.asyncio
async def test_query() -> None:
    rez = (
        db.UserResolver()
        .filter_by(name="Paul")
        .friends(db.UserResolver().limit(10).offset(0).friends())
        .limit(10)
        .offset(0)
        .order_by(".created_at DESC")
    )
    await rez.query()
