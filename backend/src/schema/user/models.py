from typing import List, Annotated, Optional
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict

from ..document.models import Document

PyObjectId = Annotated[str, BeforeValidator(str)]


class PostgresTable(BaseModel):
    """PostgreSQL table metadata"""

    table_name: str = Field(..., description="Name of the table in PostgreSQL")
    original_filename: str = Field(..., description="Original CSV filename")
    row_count: int = Field(..., description="Number of rows in the table")
    column_count: int = Field(..., description="Number of columns in the table")
    columns: List[str] = Field(default=[], description="List of column names")
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class PostgresDatabase(BaseModel):
    """PostgreSQL database metadata"""

    database_name: str = Field(..., description="Name of the database in PostgreSQL")
    table_list: List[PostgresTable] = Field(
        default=[], description="List of tables in this database"
    )
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class Message(BaseModel):
    """New message"""

    id: Optional[PyObjectId] = Field(
        alias="_id", default=None, description="ID of message"
    )
    role: str = Field(..., description="Role of message including user or AIMessage")
    content: str = Field(default="", description="Content of the message")
    created_at: Optional[int] = None
    processing_steps: Optional[List[dict]] = Field(
        default=None, description="Processing steps for agent responses"
    )
    retrieved_documents: Optional[List[dict]] = Field(
        default=None, description="Retrieved documents for RAG responses"
    )


class Chat(BaseModel):
    """Chat collection for selected chat"""

    id: Optional[PyObjectId] = Field(
        alias="_id", default=None, description="ID of the chat"
    )
    name: Optional[str] = Field(default=None, description="Chat name")
    created_at: Optional[int] = None
    message_list: List[Message] = Field(
        default=[], description="List of message within a chat"
    )


class User(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None, description="User ID")
    name: Optional[str] = Field(default=None, description="User name")
    chat_list: Optional[List[Chat]] = Field(default=[], description="List of all chats")
    doc_list: List[Document] = Field(
        default=[], description="List of uploaded documents"
    )
    database_list: List[PostgresDatabase] = Field(
        default=[], description="List of PostgreSQL databases with their tables"
    )

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class UserCollection(BaseModel):
    users: List[User]
