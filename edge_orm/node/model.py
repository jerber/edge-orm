import typing as T
from uuid import UUID
from pydantic import BaseModel, PrivateAttr, Field


InsertType = T.TypeVar("InsertType", bound=BaseModel)
PatchType = T.TypeVar("PatchType", bound=BaseModel)


class Node(BaseModel, T.Generic[InsertType, PatchType]):
    id: UUID = Field(..., allow_mutation=False)

    class Config:
        validate_assignment = True
