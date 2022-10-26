import typing as T
from uuid import UUID
from pydantic import BaseModel, PrivateAttr, Field


# InsertType = T.TypeVar("InsertType", bound=BaseModel)
# PatchType = T.TypeVar("PatchType", bound=BaseModel)


class Node(BaseModel):
    id: UUID = Field(..., allow_mutation=False)

    class Config:
        allow_mutation = False
        validate_assignment = True
        arbitrary_types_allowed = True

    class Edge:
        appendix_properties: T.ClassVar[set[str]]
        computed_properties: T.ClassVar[set[str]]

    """
    @classmethod
    def appendix_properties(cls) -> set[str]:
        return cls.Edge.appendix_properties
    """
