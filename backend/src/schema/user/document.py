from typing import List, Annotated, Optional
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict

PyObjectId = Annotated[str, BeforeValidator(str)]


class Document(BaseModel):
    id: Optional[PyObjectId] = Field(
        alias="_id", default=None, description="Document ID"
    )
    s3_path: str = Field(..., description="Location of the document (in S3)")
    title: str = Field(..., description="Title of the uploaded document")
    size: Optional[float] = Field(default=None, description="Size of the document (MB)")
    uploaded_date: Optional[int] = Field(default=None, description='Uploaded date')
    
    indexed: Optional[bool] = Field(
        default=None, description="Whether the document is indexed for searching"
    )
    chunked: Optional[bool] = Field(
        default=None, description="Whether the document is chunked for searching"
    )


class DocumentCollection(BaseModel):
    documents: List[Document] = Field(default=[], description="List of all document")
