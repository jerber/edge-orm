import typing as T
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, PrivateAttr
from edgedb import AsyncIOClient


class PropertyCardinality(str, Enum):
    ONE = "ONE"
    MANY = "MANY"


class Cardinality(str, Enum):
    One = "One"
    Many = "Many"


class FieldInfo(BaseModel):
    cast: str
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

    node_edgedb_conversion_map: CONVERSION_MAP
    insert_edgedb_conversion_map: CONVERSION_MAP
    patch_edgedb_conversion_map: CONVERSION_MAP

    insert_link_conversion_map: CONVERSION_MAP

    class Config:
        arbitrary_types_allowed = True


COMPUTED = dict[str, T.Any]


class Node(BaseModel):
    id: UUID

    EdgeConfig: T.ClassVar[EdgeConfigBase]

    _computed: COMPUTED = PrivateAttr(default=dict())

    @property
    def computed(self) -> COMPUTED:
        return self._computed

    class Config:
        allow_mutation = False
        validate_assignment = True
        arbitrary_types_allowed = True


NodeType = T.TypeVar("NodeType", bound=Node)


class Insert(BaseModel):
    pass

    class Config:
        allow_mutation = True
        validate_assignment = True
        arbitrary_types_allowed = True


class Patch(BaseModel):
    pass

    class Config:
        allow_mutation = True
        validate_assignment = True
        arbitrary_types_allowed = True
