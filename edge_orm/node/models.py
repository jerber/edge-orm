import typing as T
from uuid import UUID
from pydantic import BaseModel, PrivateAttr, Field
from edgedb import AsyncIOClient

CONVERSION_MAP = dict[str, dict[str, str | bool]]


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


class Node(BaseModel):
    id: UUID = Field(..., allow_mutation=False)

    class Config:
        allow_mutation = False
        validate_assignment = True
        arbitrary_types_allowed = True

    EdgeConfig: T.ClassVar[EdgeConfigBase]


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
