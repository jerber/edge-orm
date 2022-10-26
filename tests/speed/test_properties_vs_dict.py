import pytest
import typing as T
import uuid
from datetime import datetime
from edge_orm import Node, UNSET
from pydantic import Field, parse_obj_as, PrivateAttr, ValidationError
from devtools import debug
import random
import time

from faker import Faker

fake = Faker()


class UserSmall(Node):
    name: str
    age: int
    created_at: datetime

    class Edge:
        appendix_properties = {"created_at"}
        computed_properties = {"names_of_friends"}


from enum import Enum


# class Unset(str, Enum):
#     UNSET = "UNSET"


# UNSET_ENUM = Unset.UNSET
# UNSET = "*_**"


class User(Node):
    name: str
    age: int
    created_at: datetime

    class Edge:
        appendix_properties = {"created_at"}
        computed_properties = {"names_of_friends"}

    # _d: dict[str, T.Any] = {}

    # prop1_: str | None = Field(None, alias="prop1")
    # prop2_: str | None = Field(None, alias="prop2")
    # prop3_: str | None = Field(None, alias="prop3")
    # prop4_: str | None = Field(None, alias="prop4")
    # prop5_: str | None = Field(None, alias="prop5")
    # prop6_: str | None = Field(None, alias="prop6")
    # prop7_: str | None = Field(None, alias="prop7")
    # prop8_: str | None = Field(None, alias="prop8")
    # prop9_: str | None = Field(None, alias="prop9")
    # prop10_: str | None = Field(None, alias="prop10")
    # prop11_: str | None = Field(None, alias="prop11")
    # prop12_: str | None = Field(None, alias="prop12")
    # prop13_: str | None = Field(None, alias="prop13")
    # prop14_: str | None = Field(None, alias="prop14")
    # prop15_: str | None = Field(None, alias="prop15")
    # prop16_: str | None = Field(None, alias="prop16")
    # prop17_: dict[str, T.Any] | None = Field(None, alias="prop17")
    # prop18_: str | None = Field(None, alias="prop18")
    # prop19_: str | None = Field(None, alias="prop19")

    prop1_: str = Field(UNSET, alias="prop1")
    prop2_: str | None = Field(UNSET, alias="prop2")
    prop3_: str | None = Field(UNSET, alias="prop3")
    prop4_: str | None = Field(UNSET, alias="prop4")
    prop5_: str | None = Field(UNSET, alias="prop5")
    prop6_: str | None = Field(UNSET, alias="prop6")
    prop7_: str | None = Field(UNSET, alias="prop7")
    prop8_: str | None = Field(UNSET, alias="prop8")
    prop9_: str | None = Field(UNSET, alias="prop9")
    prop10_: str | None = Field(UNSET, alias="prop10")
    prop11_: str | None = Field(UNSET, alias="prop11")
    prop12_: str | None = Field(UNSET, alias="prop12")
    prop13_: str | None = Field(UNSET, alias="prop13")
    prop14_: str | None = Field(UNSET, alias="prop14")
    prop15_: int | None = Field(UNSET, alias="prop15")
    prop16_: str | None = Field(UNSET, alias="prop16")
    prop17_: dict[str, T.Any] | None = Field(UNSET, alias="prop17")
    prop18_: str | None = Field(UNSET, alias="prop18")
    prop19_: str | None = Field(UNSET, alias="prop19")

    @property
    def prop1(self) -> str | None:
        return self.prop1_

    @property
    def prop2(self) -> str | None:
        return self.prop1_

    @property
    def prop3(self) -> str | None:
        return self.prop1_

    @property
    def prop4(self) -> str | None:
        return self.prop1_

    @property
    def prop5(self) -> str | None:
        return self.prop1_

    @property
    def prop6(self) -> str | None:
        return self.prop1_

    @property
    def prop7(self) -> str | None:
        return self.prop1_

    @property
    def prop8(self) -> str | None:
        return self.prop1_

    @property
    def prop9(self) -> str | None:
        return self.prop1_


def test_props() -> None:
    u = User(id=uuid.uuid4(), name="Juan", age=10, created_at=datetime.now())
    assert u.prop1_ is UNSET
    u = User(
        id=uuid.uuid4(), name="Juan", age=10, created_at=datetime.now(), prop1="hi"
    )
    assert u.prop1_ == "hi"
    with pytest.raises(ValidationError) as e:
        u = User(
            id=uuid.uuid4(), name="Juan", age=10, created_at=datetime.now(), prop1=None
        )
        assert u.prop1_ is None


def test_speeds(times: int, user_cls: T.Type[UserSmall] | T.Type[User]) -> float:
    kwargs_lst = []
    for x in range(times):
        kwargs_lst.append(
            {
                "id": uuid.uuid4(),
                "name": fake.name(),
                "age": random.randint(1, 100),
                "created_at": datetime.now(),
            }
        )
    start = time.process_time()
    smalls = [user_cls(**k) for k in kwargs_lst]
    # smalls = parse_obj_as(list[user_cls], kwargs_lst)
    took_micros = (time.process_time() - start) * 1_000_000
    print(f"took {took_micros} ms, {took_micros / len(smalls)} per")
    return took_micros / len(smalls)


def test_speeds_times(times: int, user_cls: T.Type[UserSmall] | T.Type[User]) -> None:
    res_lst = []
    for _ in range(times):
        res_lst.append(test_speeds(times=1_000, user_cls=user_cls))
    print("avg", sum(res_lst) / len(res_lst))


if __name__ == "__main__":
    test_speeds_times(user_cls=User, times=10)


# learings:
# changing Field(UNSET) -> Field(None) is a 2x speedup
# so, there are benefits to having fn_ -> pydantic validates them and unsing new Unset it's not so slow, only 2x,
# will try this approach first. also make sure for dict it works by taking away _
