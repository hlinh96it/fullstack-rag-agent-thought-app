from fastapi import APIRouter, HTTPException, Body
from bson import ObjectId
from pymongo import ReturnDocument

from src.schema.user.models import UserCollection, User
from src.dependencies import MongoDependency, AWSDependency

import logging

logger = logging.getLogger(__name__)


user_router = APIRouter(tags=["user"])


@user_router.get(
    "/", description="Get all user metadata", response_model=UserCollection
)
async def get_all_user(mongodb_client: MongoDependency):
    try:
        response = await mongodb_client.collection.find().to_list(length=None)
        return UserCollection(users=response)
    except Exception as e:
        logger.error(f"Failed to get user metadata: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get user metadata: {str(e)}"
        )


@user_router.post(
    "/",
    description="Create new user",
    response_model=User,
    response_model_by_alias=True,
)
async def create_user(
    mongodb_client: MongoDependency, aws_client: AWSDependency, user: User
) -> User:
    new_user = user.model_dump(by_alias=True, exclude={"id"})

    try:
        response = await mongodb_client.collection.find_one({"name": new_user["name"]})
        if response:
            logger.info(f"Username: {new_user['name']} existed")
            return response
        else:
            response = await mongodb_client.collection.insert_one(new_user)
            new_user["_id"] = response.inserted_id
    except Exception as e:
        logger.error(f"Failed to create new user in MongoDB: {e}")
        raise HTTPException(
            status_code=404, detail="Failed to create new user in MongoDB"
        )

    try:
        folder_key = f"{new_user['_id']}/"
        bucket_name = aws_client.settings.bucket_name

        response = aws_client.s3_client.list_objects_v2(
            Bucket=bucket_name, Prefix=folder_key, MaxKeys=1
        )
        if "Contents" in response and len(response["Contents"]) > 0:
            logger.warning(f"Folder for user {new_user['_id']} already existed")
        else:
            aws_client.s3_client.put_object(
                Bucket=bucket_name,
                Key=folder_key,
                Body=b"",
                ContentType="application/x-directory",
            )
            logger.info(f'Created folder for user {new_user["_id"]} successfully')
    except Exception as e:
        logger.error(f"Failed to create new user folder in AWS S3: {e}")
        raise HTTPException(
            status_code=404, detail="Failed to create new user in AWS S3"
        )

    return User(**new_user)


@user_router.put(
    "/{user_id}",
    description="Update user data",
    response_model=User,
    response_model_by_alias=False,
)
async def update_user(
    user_id: str, mongo_client: MongoDependency, user: dict = Body(...)
):
    new_user_data = {key: value for key, value in user.items() if value is not None}

    update_user = await mongo_client.collection.find_one_and_update(
        filter={"_id": ObjectId(user_id)},
        update={"$set": new_user_data},
        return_document=ReturnDocument.AFTER,
    )

    if update_user:
        return update_user
    else:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
