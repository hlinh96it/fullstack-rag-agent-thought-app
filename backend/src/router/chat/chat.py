from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from bson.errors import InvalidId

from src.schema.user.models import Chat, User, Message
from src.dependencies import MongoDependency


chat_router = APIRouter(tags=["chat"])


@chat_router.get(
    "/{user_id}",
    description="Get all chat of user",
    response_model=List[Chat],
    response_model_by_alias=False,
)
async def get_all_chat(user_id: str, mongodb_client: MongoDependency) -> List[Chat]:
    try:
        response = await mongodb_client.collection.find_one({"_id": ObjectId(user_id)})
        if response:
            # Convert ObjectId to string for JSON serialization
            response["_id"] = str(response["_id"])
            user_data = User(**response)
            return user_data.chat_list if user_data.chat_list else []
        else:
            raise HTTPException(status_code=404, detail=f"User not found: {user_id}")
    except InvalidId:
        raise HTTPException(
            status_code=400, detail=f"Invalid user_id format: {user_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to get chat: {e}")


@chat_router.post(
    "/{user_id}",
    description="Create new chat",
    response_model=Chat,
    response_model_by_alias=True,
)
async def create_new_chat(
    user_id: str, chat: Chat, mongo_client: MongoDependency
) -> Chat:
    new_chat = chat.model_dump(by_alias=True, exclude={"id"})
    new_chat["_id"] = ObjectId()
    try:
        await mongo_client.collection.update_one(
            {"_id": ObjectId(user_id)}, {"$push": {"chat_list": new_chat}}
        )
    except InvalidId:
        raise HTTPException(
            status_code=400, detail=f"Invalid user_id format: {user_id}"
        )

    new_chat["_id"] = str(new_chat["_id"])
    return Chat(**new_chat)


@chat_router.delete(
    "/{user_id}/{chat_id}",
    description="Delete selected chat",
    response_model=User,
    response_model_by_alias=False,
)
async def delete_chat(user_id: str, chat_id: str, database: MongoDependency):
    try:
        response = await database.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"chat_list": {"_id": ObjectId(chat_id)}}},
        )
        if response.modified_count == 1:
            return await database.collection.find_one({"_id": ObjectId(user_id)})
        else:
            raise HTTPException(status_code=404, detail=f"Chat {chat_id} not found")
    except InvalidId:
        raise HTTPException(
            status_code=400, detail=f"Invalid user_id or chat_id format"
        )


@chat_router.post(
    "/{user_id}/{chat_id}",
    description="Add new message to selected chat",
    response_model=Chat,
    response_model_by_alias=False,
)
async def add_message(
    user_id: str, chat_id: str, message: Message, mongo_client: MongoDependency
):
    new_message = message.model_dump(by_alias=True, exclude={"id"})
    new_message["_id"] = ObjectId()

    try:
        response = await mongo_client.collection.update_one(
            {"_id": ObjectId(user_id), "chat_list._id": ObjectId(chat_id)},
            {"$push": {"chat_list.$.message_list": new_message}},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add new message: {e}")

    # fetch and return updated chat
    try:
        user_data = await mongo_client.collection.find_one(
            {"_id": ObjectId(user_id)},
            {"chat_list": {"$elemMatch": {"_id": ObjectId(chat_id)}}},
        )
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Failed to fetch updated chat: {e}"
        )

    if user_data:
        return Chat(**user_data["chat_list"][0])
