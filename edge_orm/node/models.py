import typing as T
from uuid import UUID
from enum import Enum
import edgedb
from pydantic import BaseModel, PrivateAttr
from edgedb import AsyncIOClient
from edge_orm.cache import Cache
from edge_orm.unset import UNSET
from .errors import NodeException

if T.TYPE_CHECKING:
    # from edge_orm.cache import Cache
    from edge_orm.resolver.model import Resolver


class PropertyCardinality(str, Enum):
    ONE = "ONE"
    MANY = "MANY"


class Cardinality(str, Enum):
    One = "One"
    Many = "Many"


class FieldInfo(BaseModel):
    cast: str
    base_cast: str | None
    cardinality: Cardinality
    readonly: bool
    required: bool


CONVERSION_MAP = dict[str, FieldInfo]


class EdgeConfigBase(BaseModel):
    model_name: str
    client: AsyncIOClient

    updatable_fields: set[str]
    exclusive_fields: set[str]

    appendix_properties: set[str]
    computed_properties: set[str]
    basemodel_properties: set[str]
    custom_annotations: set[str]
    mutate_on_update: dict[str, str]

    node_edgedb_conversion_map: CONVERSION_MAP
    insert_edgedb_conversion_map: CONVERSION_MAP
    patch_edgedb_conversion_map: CONVERSION_MAP

    insert_link_conversion_map: CONVERSION_MAP

    class Config:
        arbitrary_types_allowed = True


COMPUTED = dict[str, T.Any]


class SetFields(BaseModel):
    _purged_unsets: bool = PrivateAttr(False)

    @property
    def set_fields_(self) -> set[str]:
        if not self._purged_unsets:
            for key in self.__fields_set__.copy():
                if getattr(self, key, None) is UNSET:
                    self.__fields_set__.remove(key)
            self._purged_unsets = True
        return self.__fields_set__


class IgnoreUnset(SetFields):
    def __setattr__(self, key: T.Any, value: T.Any) -> None:
        if value is UNSET:
            return
        super().__setattr__(key, value)


class Insert(IgnoreUnset):
    pass

    class Config:
        allow_mutation = True
        validate_assignment = True
        arbitrary_types_allowed = True
        anystr_strip_whitespace = True


class Patch(IgnoreUnset):
    pass

    class Config:
        allow_mutation = True
        validate_assignment = True
        arbitrary_types_allowed = True
        anystr_strip_whitespace = True


class classproperty(property):
    def __get__(self, owner_self, owner_cls):  # type: ignore
        return self.fget(owner_cls)  # type: ignore


class Node(SetFields):
    id: UUID

    EdgeConfig: T.ClassVar[EdgeConfigBase]

    _computed: COMPUTED = PrivateAttr(default=dict())

    _cache: "Cache" = PrivateAttr(default_factory=Cache)

    _used_resolver: "Resolver" = PrivateAttr(None)  # type: ignore

    @property
    def computed(self) -> COMPUTED:
        return self._computed

    async def resolve(
        self,
        *,
        edge_name: str,
        edge_resolver: "Resolver",
        cache_only: bool = True,
        client: edgedb.AsyncIOClient | None = None,
    ) -> T.Any:
        val = self._cache.val_or_unset(edge=edge_name, resolver=edge_resolver)
        if val is UNSET:
            if cache_only:
                raise NodeException(
                    f"Could not get {edge_name} from the cache, and settings are cache_only."
                )
            else:
                new_r = self._used_resolver.__class__()
                # UserResolver().friends(edge_resolver)
                getattr(new_r, edge_name)(edge_resolver)
                this_node = await new_r._gerror(
                    field_name="id", value=self.id, client=client
                )
                new_val = await getattr(this_node, edge_name)(edge_resolver)
                self._cache.add(edge=edge_name, resolver=edge_resolver, val=new_val)
                return new_val
        return val

    """
    # TODO time the diff between initing it vs this property method
    @property
    def _cache(self) -> "Cache":
        if not self.__cache:
            self.__cache = Cache()
        return self.__cache
    """
    """
    @classproperty
    def Insert(self) -> T.Type[Insert]:  # example of how this could work
        return Insert
    """

    class Config:
        allow_mutation = False
        validate_assignment = True
        arbitrary_types_allowed = True
