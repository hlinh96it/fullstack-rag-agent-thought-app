from typing import List, Annotated, Optional
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict

from ..document.models import Document

PyObjectId = Annotated[str, BeforeValidator(str)]


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
    name: Optional[str] = Field(description="User name")
    chat_list: Optional[List[Chat]] = Field(default=[], description="List of all chats")
    doc_list: List[Document] = Field(
        default=[], description="List of uploaded documents"
    )

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class UserCollection(BaseModel):
    users: List[User]
