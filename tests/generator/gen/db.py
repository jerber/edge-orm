from __future__ import annotations
import os
import typing as T
from enum import Enum
from datetime import datetime, date, timedelta
from uuid import UUID
from decimal import Decimal
from edgedb import RelativeDuration, AsyncIOClient, create_async_client
from pydantic import BaseModel, Field, PrivateAttr, validator
from edge_orm.node.models import Cardinality, FieldInfo
from edge_orm import (
    Node,
    Insert,
    Patch,
    EdgeConfigBase,
    Resolver,
    NodeException,
    ResolverException,
    UNSET,
    UnsetType,
    validators,
    errors,
    resolver_enums,
)

FilterConnector = resolver_enums.FilterConnector
from .db_enums import *

CLIENT = create_async_client(dsn=os.environ["EDGEDB_DSN"])
from pydantic import EmailStr


class User(Node):
    id: UUID = Field(...)
    phone_number: str = Field(...)
    last_updated_at_: T.Union[datetime, UnsetType] = Field(
        UNSET, alias="last_updated_at"
    )
    created_at_: T.Union[datetime, UnsetType] = Field(UNSET, alias="created_at")
    name: str = Field(...)
    age: T.Optional[int] = Field(None)
    user_role_: T.Union[T.Optional[UserRole], UnsetType] = Field(
        UNSET, alias="user_role"
    )
    images_: T.Union[T.Optional[T.List[str]], UnsetType] = Field(UNSET, alias="images")
    email_: T.Union[T.Optional[EmailStr], UnsetType] = Field(UNSET, alias="email")
    names_of_friends_: T.Union[T.Optional[T.Set[str]], UnsetType] = Field(
        UNSET, alias="names_of_friends"
    )

    @property
    def last_updated_at(self) -> datetime:
        # if self.last_updated_at_ is UNSET:
        if "last_updated_at_" not in self.__fields_set__:
            raise errors.AppendixPropertyException("last_updated_at is unset")
        return self.last_updated_at_  # type: ignore

    @property
    def created_at(self) -> datetime:
        # if self.created_at_ is UNSET:
        if "created_at_" not in self.__fields_set__:
            raise errors.AppendixPropertyException("created_at is unset")
        return self.created_at_  # type: ignore

    @property
    def user_role(self) -> T.Optional[UserRole]:
        # if self.user_role_ is UNSET:
        if "user_role_" not in self.__fields_set__:
            raise errors.AppendixPropertyException("user_role is unset")
        return self.user_role_  # type: ignore

    @property
    def images(self) -> T.Optional[T.List[str]]:
        # if self.images_ is UNSET:
        if "images_" not in self.__fields_set__:
            raise errors.AppendixPropertyException("images is unset")
        return self.images_  # type: ignore

    @property
    def email(self) -> T.Optional[EmailStr]:
        # if self.email_ is UNSET:
        if "email_" not in self.__fields_set__:
            raise errors.AppendixPropertyException("email is unset")
        return self.email_  # type: ignore

    @property
    def names_of_friends(self) -> T.Optional[T.Set[str]]:
        # if self.names_of_friends_ is UNSET:
        if "names_of_friends_" not in self.__fields_set__:
            raise errors.ComputedPropertyException("names_of_friends is unset")
        return self.names_of_friends_  # type: ignore

    EdgeConfig: T.ClassVar[EdgeConfigBase] = EdgeConfigBase(
        model_name="User",
        client=CLIENT,
        updatable_fields={
            "age",
            "created_at",
            "email",
            "friends",
            "images",
            "last_updated_at",
            "name",
            "user_role",
        },
        exclusive_fields={"id", "phone_number"},
        appendix_properties={
            "created_at",
            "email",
            "images",
            "last_updated_at",
            "user_role",
        },
        computed_properties={"names_of_friends"},
        basemodel_properties={"email"},
        custom_annotations=set(),
        node_edgedb_conversion_map={
            "id": FieldInfo(
                cast="std::uuid",
                cardinality=Cardinality.One,
                readonly=True,
                required=True,
            ),
            "phone_number": FieldInfo(
                cast="std::str",
                cardinality=Cardinality.One,
                readonly=True,
                required=True,
            ),
            "last_updated_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "created_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "name": FieldInfo(
                cast="std::str",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "age": FieldInfo(
                cast="std::int16",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
            "user_role": FieldInfo(
                cast="default::UserRole",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
            "images": FieldInfo(
                cast="array<std::json>",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
            "email": FieldInfo(
                cast="std::str",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
            "names_of_friends": FieldInfo(
                cast="std::str",
                cardinality=Cardinality.Many,
                readonly=False,
                required=False,
            ),
        },
        insert_edgedb_conversion_map={
            "id": FieldInfo(
                cast="std::uuid",
                cardinality=Cardinality.One,
                readonly=True,
                required=True,
            ),
            "phone_number": FieldInfo(
                cast="std::str",
                cardinality=Cardinality.One,
                readonly=True,
                required=True,
            ),
            "last_updated_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "created_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "name": FieldInfo(
                cast="std::str",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "age": FieldInfo(
                cast="std::int16",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
            "user_role": FieldInfo(
                cast="default::UserRole",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
            "images": FieldInfo(
                cast="array<std::json>",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
            "email": FieldInfo(
                cast="std::str",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
        },
        patch_edgedb_conversion_map={
            "last_updated_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "created_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "name": FieldInfo(
                cast="std::str",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "age": FieldInfo(
                cast="std::int16",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
            "user_role": FieldInfo(
                cast="default::UserRole",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
            "images": FieldInfo(
                cast="array<std::json>",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
            "email": FieldInfo(
                cast="std::str",
                cardinality=Cardinality.One,
                readonly=False,
                required=False,
            ),
        },
        insert_link_conversion_map={
            "friends": FieldInfo(
                cast="User",
                cardinality=Cardinality.Many,
                readonly=False,
                required=False,
            )
        },
    )


class UserInsert(Insert):
    id: T.Union[UUID, UnsetType] = Field(UNSET)
    phone_number: str
    last_updated_at: T.Union[datetime, UnsetType] = Field(UNSET)
    created_at: T.Union[datetime, UnsetType] = Field(UNSET)
    name: str
    age: T.Union[int, None, UnsetType] = Field(UNSET)
    user_role: T.Union[UserRole, None, UnsetType] = Field(UNSET)
    images: T.Union[T.List[str], None, UnsetType] = Field(UNSET)
    email: T.Union[EmailStr, None, UnsetType] = Field(UNSET)
    friends: T.Optional[UserResolver] = None


class UserPatch(Patch):
    last_updated_at: T.Union[T.Optional[datetime], UnsetType] = Field(UNSET)
    created_at: T.Union[T.Optional[datetime], UnsetType] = Field(UNSET)
    name: T.Union[str, UnsetType] = Field(UNSET)
    age: T.Union[T.Optional[int], UnsetType] = Field(UNSET)
    user_role: T.Union[T.Optional[UserRole], UnsetType] = Field(UNSET)
    images: T.Union[T.Optional[T.List[str]], UnsetType] = Field(UNSET)
    email: T.Union[T.Optional[EmailStr], UnsetType] = Field(UNSET)
    friends: T.Union[T.Optional[UserResolver], UnsetType] = Field(
        default_factory=UnsetType
    )


class UserResolver(Resolver[User, UserInsert, UserPatch]):
    _node_cls = User

    def friends(
        self, _: T.Optional[UserResolver] = None, /, make_first: bool = False
    ) -> UserResolver:
        self._nested_resolvers.add(
            "friends", _ or UserResolver(), make_first=make_first
        )
        return self

    def friends__count(
        self, _: T.Optional[UserResolver] = None, /, make_first: bool = False
    ) -> UserResolver:
        rez = _ or UserResolver()
        rez.is_count = True
        self._nested_resolvers.add("friends__count", rez, make_first=make_first)
        return self

    async def get(
        self,
        *,
        client: AsyncIOClient | None = None,
        id: T.Optional[T.Any] = None,
        phone_number: T.Optional[T.Any] = None,
    ) -> User | None:
        return await self._get(
            client=client, **{"id": id, "phone_number": phone_number}
        )

    async def gerror(
        self,
        *,
        client: AsyncIOClient = None,
        id: T.Optional[T.Any] = None,
        phone_number: T.Optional[T.Any] = None,
    ) -> User:
        return await self._gerror(
            client=client, **{"id": id, "phone_number": phone_number}
        )

    def filter_by(
        self,
        filter_connector: FilterConnector = FilterConnector.AND,
        age: T.Optional[T.Any] = None,
        created_at: T.Optional[T.Any] = None,
        email: T.Optional[T.Any] = None,
        id: T.Optional[T.Any] = None,
        images: T.Optional[T.Any] = None,
        last_updated_at: T.Optional[T.Any] = None,
        name: T.Optional[T.Any] = None,
        names_of_friends: T.Optional[T.Any] = None,
        phone_number: T.Optional[T.Any] = None,
        user_role: T.Optional[T.Any] = None,
    ) -> UserResolver:
        return self._filter_by(
            connector=filter_connector,
            **{
                "age": age,
                "created_at": created_at,
                "email": email,
                "id": id,
                "images": images,
                "last_updated_at": last_updated_at,
                "name": name,
                "names_of_friends": names_of_friends,
                "phone_number": phone_number,
                "user_role": user_role,
            },
        )

    def filter_in(
        self,
        filter_connector: FilterConnector = FilterConnector.AND,
        age: T.Optional[T.List[T.Any]] = None,
        created_at: T.Optional[T.List[T.Any]] = None,
        email: T.Optional[T.List[T.Any]] = None,
        id: T.Optional[T.List[T.Any]] = None,
        images: T.Optional[T.List[T.Any]] = None,
        last_updated_at: T.Optional[T.List[T.Any]] = None,
        name: T.Optional[T.List[T.Any]] = None,
        names_of_friends: T.Optional[T.List[T.Any]] = None,
        phone_number: T.Optional[T.List[T.Any]] = None,
        user_role: T.Optional[T.List[T.Any]] = None,
    ) -> UserResolver:
        return self._filter_in(
            connector=filter_connector,
            **{
                "age": age,
                "created_at": created_at,
                "email": email,
                "id": id,
                "images": images,
                "last_updated_at": last_updated_at,
                "name": name,
                "names_of_friends": names_of_friends,
                "phone_number": phone_number,
                "user_role": user_role,
            },
        )

    def include(
        self,
        *,
        created_at: bool = False,
        email: bool = False,
        images: bool = False,
        last_updated_at: bool = False,
        names_of_friends: bool = False,
        user_role: bool = False,
    ) -> UserResolver:
        fields_to_include: set[str] = set()
        if created_at is True:
            fields_to_include.add("created_at")
        if email is True:
            fields_to_include.add("email")
        if images is True:
            fields_to_include.add("images")
        if last_updated_at is True:
            fields_to_include.add("last_updated_at")
        if names_of_friends is True:
            fields_to_include.add("names_of_friends")
        if user_role is True:
            fields_to_include.add("user_role")
        return self.include_fields(*fields_to_include)


class DateModel(Node):
    id: UUID = Field(...)
    created_at: datetime = Field(...)
    last_updated_at: datetime = Field(...)

    EdgeConfig: T.ClassVar[EdgeConfigBase] = EdgeConfigBase(
        model_name="DateModel",
        client=CLIENT,
        updatable_fields={"created_at", "last_updated_at"},
        exclusive_fields={"id"},
        appendix_properties=set(),
        computed_properties=set(),
        basemodel_properties=set(),
        custom_annotations=set(),
        node_edgedb_conversion_map={
            "id": FieldInfo(
                cast="std::uuid",
                cardinality=Cardinality.One,
                readonly=True,
                required=True,
            ),
            "created_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "last_updated_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
        },
        insert_edgedb_conversion_map={
            "id": FieldInfo(
                cast="std::uuid",
                cardinality=Cardinality.One,
                readonly=True,
                required=True,
            ),
            "created_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "last_updated_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
        },
        patch_edgedb_conversion_map={
            "created_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
            "last_updated_at": FieldInfo(
                cast="std::datetime",
                cardinality=Cardinality.One,
                readonly=False,
                required=True,
            ),
        },
        insert_link_conversion_map={},
    )


class DateModelInsert(Insert):
    id: T.Union[UUID, UnsetType] = Field(UNSET)
    created_at: T.Union[datetime, UnsetType] = Field(UNSET)
    last_updated_at: T.Union[datetime, UnsetType] = Field(UNSET)


class DateModelPatch(Patch):
    created_at: T.Union[T.Optional[datetime], UnsetType] = Field(UNSET)
    last_updated_at: T.Union[T.Optional[datetime], UnsetType] = Field(UNSET)


class DateModelResolver(Resolver[DateModel, DateModelInsert, DateModelPatch]):
    _node_cls = DateModel

    async def get(
        self, *, client: AsyncIOClient | None = None, id: T.Optional[T.Any] = None
    ) -> DateModel | None:
        return await self._get(client=client, **{"id": id})

    async def gerror(
        self, *, client: AsyncIOClient = None, id: T.Optional[T.Any] = None
    ) -> DateModel:
        return await self._gerror(client=client, **{"id": id})

    def filter_by(
        self,
        filter_connector: FilterConnector = FilterConnector.AND,
        created_at: T.Optional[T.Any] = None,
        id: T.Optional[T.Any] = None,
        last_updated_at: T.Optional[T.Any] = None,
    ) -> DateModelResolver:
        return self._filter_by(
            connector=filter_connector,
            **{"created_at": created_at, "id": id, "last_updated_at": last_updated_at},
        )

    def filter_in(
        self,
        filter_connector: FilterConnector = FilterConnector.AND,
        created_at: T.Optional[T.List[T.Any]] = None,
        id: T.Optional[T.List[T.Any]] = None,
        last_updated_at: T.Optional[T.List[T.Any]] = None,
    ) -> DateModelResolver:
        return self._filter_in(
            connector=filter_connector,
            **{"created_at": created_at, "id": id, "last_updated_at": last_updated_at},
        )


UserInsert.update_forward_refs()
DateModelInsert.update_forward_refs()

User.update_forward_refs()
DateModel.update_forward_refs()
