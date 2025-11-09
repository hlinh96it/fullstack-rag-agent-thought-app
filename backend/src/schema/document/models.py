from typing import List, Annotated, Optional
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict

PyObjectId = Annotated[str, BeforeValidator(str)]


class DocumentMetadata(BaseModel):
    title: str = Field(..., description="Document title")
    authors: List[str] = Field(..., description="List of authors")
    abstract: str = Field(..., description="Abstract of the paper")
    categories: List[str] = Field(default_factory=list, description="Paper categories")
    published_date: str = Field(..., description="Publication date")


class PaperSection(BaseModel):
    """Represents a section of a paper."""

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    level: int = Field(default=1, description="Section hierarchy level")


class PaperFigure(BaseModel):
    """Represents a figure in a paper."""

    caption: str = Field(..., description="Figure caption")
    id: str = Field(..., description="Figure identifier")


class PaperTable(BaseModel):
    """Represents a table in a paper."""

    caption: str = Field(..., description="Table caption")
    id: str = Field(..., description="Table identifier")


class DocumentContent(BaseModel):
    sections: List[PaperSection] = Field(
        default_factory=list, description="Paper sections"
    )
    figures: List[PaperFigure] = Field(default_factory=list, description="Figures")
    tables: List[PaperTable] = Field(default_factory=list, description="Tables")
    raw_text: str = Field(..., description="Full extracted text")
    references: List[str] = Field(default_factory=list, description="References")


class ParsedDocument(BaseModel):
    doc_metadata: DocumentMetadata = Field(..., description="Paper metadata")
    doc_content: Optional[DocumentContent] = Field(
        default=None, description="Content extracted from PDF"
    )


class Document(BaseModel):
    id: Optional[PyObjectId] = Field(
        alias="_id", default=None, description="Document ID"
    )
    s3_path: str = Field(..., description="Location of the document (in S3)")
    title: str = Field(..., description="Title of the uploaded document")
    size: Optional[float] = Field(default=None, description="Size of the document (MB)")
    uploaded_date: Optional[int] = Field(default=None, description="Uploaded date")

    chunked: Optional[bool] = Field(
        default=False,
        description="Whether the document is chunked (True/False) or 'processing' if chunking in progress",
    )
    chunk_error: Optional[str] = Field(
        default=None, description="Error message if chunking failed"
    )
    indexed: Optional[bool] = Field(
        default=None, description="Whether the document is indexed for searching"
    )
    indexed_error: Optional[str] = Field(
        default=None, description='Error message if indexing failed'
    )


class DocumentCollection(BaseModel):
    documents: List[Document] = Field(default=[], description="List of all document")
