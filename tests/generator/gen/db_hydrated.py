from __future__ import annotations
import os
import typing as T
from enum import Enum
from datetime import datetime, date, timedelta
from uuid import UUID
from decimal import Decimal
from edgedb import RelativeDuration, AsyncIOClient, create_async_client
from pydantic import BaseModel, Field, PrivateAttr, validator
from edge_orm.node.models import Cardinality, FieldInfo, classproperty
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
from . import db_enums as enums
from tests.models.mixin import ResolverMixin

CLIENT = create_async_client(dsn=os.environ["EDGEDB_DSN"])
CACHE_ONLY: bool = True
from pydantic import EmailStr
from tests.models import Image


class User(Node):
    id: UUID = Field(...)
    phone_number: str = Field(...)
    last_updated_at_: T.Union[datetime, UnsetType] = Field(
        UNSET, alias="last_updated_at"
    )
    created_at_: T.Union[datetime, UnsetType] = Field(UNSET, alias="created_at")
    name: str = Field(...)
    age: T.Optional[int] = Field(None)
    user_role_: T.Union[T.Optional[enums.UserRole], UnsetType] = Field(
        UNSET, alias="user_role"
    )
    images_: T.Union[T.Optional[T.List[Image]], UnsetType] = Field(
        UNSET, alias="images"
    )
    email_: T.Union[T.Optional[EmailStr], UnsetType] = Field(UNSET, alias="email")
    names_of_friends_: T.Union[T.Optional[T.Set[str]], UnsetType] = Field(
        UNSET, alias="names_of_friends"
    )
    ids_of_friends_: T.Union[T.Optional[T.Set[UUID]], UnsetType] = Field(
        UNSET, alias="ids_of_friends"
    )

    _from_str = validator("images_", pre=True, allow_reuse=True)(validators.from_str)

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
    def user_role(self) -> T.Optional[enums.UserRole]:
        # if self.user_role_ is UNSET:
        if "user_role_" not in self.__fields_set__:
            raise errors.AppendixPropertyException("user_role is unset")
        return self.user_role_  # type: ignore

    @property
    def images(self) -> T.Optional[T.List[Image]]:
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

    @property
    def ids_of_friends(self) -> T.Optional[T.Set[UUID]]:
        # if self.ids_of_friends_ is UNSET:
        if "ids_of_friends_" not in self.__fields_set__:
            raise errors.ComputedPropertyException("ids_of_friends is unset")
        return self.ids_of_friends_  # type: ignore

    async def friends(
        self,
        resolver: UserResolver = None,
        cache_only: bool = CACHE_ONLY,
        client: AsyncIOClient | None = None,
    ) -> T.Optional[T.List[User]]:
        return await self.resolve(
            edge_name="friends",
            edge_resolver=resolver or UserResolver(),
            cache_only=cache_only,
            client=client,
        )

    async def friends_Count(
        self,
        resolver: UserResolver = None,
        cache_only: bool = CACHE_ONLY,
        client: AsyncIOClient | None = None,
    ) -> int:
        rez = resolver or UserResolver()
        rez.is_count = True
        return await self.resolve(
            edge_name="friends_Count",
            edge_resolver=rez,
            cache_only=cache_only,
            client=client,
        )

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
        computed_properties={"ids_of_friends", "names_of_friends"},
        basemodel_properties={"email", "images"},
        custom_annotations=set(),
        mutate_on_update={"last_updated_at": "datetime_current()"},
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
            "ids_of_friends": FieldInfo(
                cast="std::uuid",
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
    user_role: T.Union[enums.UserRole, None, UnsetType] = Field(UNSET)
    images: T.Union[T.List[Image], None, UnsetType] = Field(UNSET)
    email: T.Union[EmailStr, None, UnsetType] = Field(UNSET)
    friends: T.Optional[UserResolver] = None


class UserPatch(Patch):
    last_updated_at: T.Union[T.Optional[datetime], UnsetType] = Field(UNSET)
    created_at: T.Union[T.Optional[datetime], UnsetType] = Field(UNSET)
    name: T.Union[str, UnsetType] = Field(UNSET)
    age: T.Union[T.Optional[int], UnsetType] = Field(UNSET)
    user_role: T.Union[T.Optional[enums.UserRole], UnsetType] = Field(UNSET)
    images: T.Union[T.Optional[T.List[Image]], UnsetType] = Field(UNSET)
    email: T.Union[T.Optional[EmailStr], UnsetType] = Field(UNSET)
    friends: T.Union[T.Optional[UserResolver], UnsetType] = Field(
        default_factory=UnsetType
    )


class UserResolver(Resolver[User, UserInsert, UserPatch], ResolverMixin):
    _node_cls = User
    _insert_cls = UserInsert
    _patch_cls = UserPatch

    def friends(
        self, _: T.Optional[UserResolver] = None, /, make_first: bool = False
    ) -> UserResolver:
        self._nested_resolvers.add(
            "friends", _ or UserResolver(), make_first=make_first
        )
        return self

    def friends_Count(
        self, _: T.Optional[UserResolver] = None, /, make_first: bool = False
    ) -> UserResolver:
        rez = _ or UserResolver()
        rez.is_count = True
        self._nested_resolvers.add("friends_Count", rez, make_first=make_first)
        return self

    async def get(
        self,
        *,
        client: AsyncIOClient | None = None,
        id: T.Optional[T.Any] = None,
        phone_number: T.Optional[T.Any] = None,
    ) -> User | None:
        kwargs = {"id": id, "phone_number": phone_number}
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if len(kwargs) != 1:
            raise ResolverException(f"Must only give one argument, received {kwargs}.")
        field_name, value = list(kwargs.items())[0]
        return await self._get(field_name=field_name, value=value, client=client)

    async def gerror(
        self,
        *,
        client: AsyncIOClient | None = None,
        id: T.Optional[T.Any] = None,
        phone_number: T.Optional[T.Any] = None,
    ) -> User:
        kwargs = {"id": id, "phone_number": phone_number}
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if len(kwargs) != 1:
            raise ResolverException(f"Must only give one argument, received {kwargs}.")
        field_name, value = list(kwargs.items())[0]
        return await self._gerror(field_name=field_name, value=value, client=client)

    async def update_one(
        self,
        patch: UserPatch,
        *,
        client: AsyncIOClient | None = None,
        id: T.Optional[T.Any] = None,
        phone_number: T.Optional[T.Any] = None,
    ) -> User:
        kwargs = {"id": id, "phone_number": phone_number}
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if len(kwargs) != 1:
            raise ResolverException(f"Must only give one argument, received {kwargs}.")
        field_name, value = list(kwargs.items())[0]
        return await self._update_one(
            patch=patch, field_name=field_name, value=value, client=client
        )

    async def delete_one(
        self,
        *,
        client: AsyncIOClient | None = None,
        id: T.Optional[T.Any] = None,
        phone_number: T.Optional[T.Any] = None,
    ) -> User:
        kwargs = {"id": id, "phone_number": phone_number}
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if len(kwargs) != 1:
            raise ResolverException(f"Must only give one argument, received {kwargs}.")
        field_name, value = list(kwargs.items())[0]
        return await self._delete_one(field_name=field_name, value=value, client=client)

    def filter_by(
        self,
        filter_connector: FilterConnector = FilterConnector.AND,
        age: T.Optional[T.Any] = None,
        created_at: T.Optional[T.Any] = None,
        email: T.Optional[T.Any] = None,
        id: T.Optional[T.Any] = None,
        ids_of_friends: T.Optional[T.Any] = None,
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
                "ids_of_friends": ids_of_friends,
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
        ids_of_friends: T.Optional[T.List[T.Any]] = None,
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
                "ids_of_friends": ids_of_friends,
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
        ids_of_friends: bool = False,
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
        if ids_of_friends is True:
            fields_to_include.add("ids_of_friends")
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
        mutate_on_update={},
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


class DateModelResolver(
    Resolver[DateModel, DateModelInsert, DateModelPatch], ResolverMixin
):
    _node_cls = DateModel
    _insert_cls = DateModelInsert
    _patch_cls = DateModelPatch

    async def get(
        self, *, client: AsyncIOClient | None = None, id: T.Optional[T.Any] = None
    ) -> DateModel | None:
        kwargs = {"id": id}
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if len(kwargs) != 1:
            raise ResolverException(f"Must only give one argument, received {kwargs}.")
        field_name, value = list(kwargs.items())[0]
        return await self._get(field_name=field_name, value=value, client=client)

    async def gerror(
        self, *, client: AsyncIOClient | None = None, id: T.Optional[T.Any] = None
    ) -> DateModel:
        kwargs = {"id": id}
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if len(kwargs) != 1:
            raise ResolverException(f"Must only give one argument, received {kwargs}.")
        field_name, value = list(kwargs.items())[0]
        return await self._gerror(field_name=field_name, value=value, client=client)

    async def update_one(
        self,
        patch: DateModelPatch,
        *,
        client: AsyncIOClient | None = None,
        id: T.Optional[T.Any] = None,
    ) -> DateModel:
        kwargs = {"id": id}
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if len(kwargs) != 1:
            raise ResolverException(f"Must only give one argument, received {kwargs}.")
        field_name, value = list(kwargs.items())[0]
        return await self._update_one(
            patch=patch, field_name=field_name, value=value, client=client
        )

    async def delete_one(
        self, *, client: AsyncIOClient | None = None, id: T.Optional[T.Any] = None
    ) -> DateModel:
        kwargs = {"id": id}
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if len(kwargs) != 1:
            raise ResolverException(f"Must only give one argument, received {kwargs}.")
        field_name, value = list(kwargs.items())[0]
        return await self._delete_one(field_name=field_name, value=value, client=client)

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

UserPatch.update_forward_refs()
DateModelPatch.update_forward_refs()

User.update_forward_refs()
DateModel.update_forward_refs()

UserResolver._edge_resolver_map: T.Dict[str, T.Union[T.Type[UserResolver]]] = {
    "friends": UserResolver,
    "friends_Count": UserResolver,
}
DateModelResolver._edge_resolver_map: T.Dict[str, T.Type[Resolver]] = {}
