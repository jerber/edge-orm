from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from pydantic import BaseModel
from edge_orm import Resolver, Node, ResolverException


class UserInsert(BaseModel):
    ...


class UserPatch(BaseModel):
    ...


class User(Node[UserInsert, UserPatch]):
    ...


class UserResolver(Resolver[User]):
    _node = User


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
