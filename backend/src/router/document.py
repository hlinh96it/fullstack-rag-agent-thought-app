from typing import List
from fastapi import APIRouter, HTTPException, Body
from bson import ObjectId

from src.schema.user.document import Document
from src.schema.user.models import User
from src.dependencies import MongoDependency


doc_router = APIRouter(tags=["doc_router"])


@doc_router.get(
    "/{user_id}",
    description="Get all document",
    response_model=List[Document],
    response_model_by_alias=False,
)
async def get_all_docs(user_id: str, mongo_client: MongoDependency) -> List[Document]:
    try:
        response = await mongo_client.collection.find_one({"_id": ObjectId(user_id)})
        if response:
            response["_id"] = str(response["_id"])
            user_data = User(**response)
            return user_data.doc_list
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get all uploaded documents: {e}"
        )


@doc_router.post(
    "/{user_id}",
    description="Add uploaded document to user doc_list",
    response_model=List[Document],
    response_model_by_alias=False,
)
async def add_doc(
    mongo_client: MongoDependency, user_id: str, docs: List[Document]
) -> List[Document]:
    doc_list = []
    for doc in docs:
        new_doc = doc.model_dump(by_alias=True, exclude={"id"})
        new_doc["_id"] = ObjectId()

        try:
            response = await mongo_client.collection.find_one_and_update(
                filter={"_id": ObjectId(user_id)},
                update={"$push": {"doc_list": new_doc}},
            )
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to add new doc to MongoDB: {e}"
            )

        new_doc["_id"] = str(new_doc["_id"])
        doc_list.append(Document(**new_doc))
    return doc_list


@doc_router.delete(
    "/{user_id}",
    description="Delete a document from user's doc_list",
    response_model=dict,
)
async def delete_doc(
    mongo_client: MongoDependency,
    user_id: str,
    body: dict = Body(...),
) -> dict:
    """
    Delete a document from user's doc_list by s3_path
    """
    s3_path = body.get("s3_path")
    if not s3_path:
        raise HTTPException(status_code=400, detail="s3_path is required")

    try:
        result = await mongo_client.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"doc_list": {"s3_path": s3_path}}},
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=404, detail="Document not found in user's doc_list"
            )

        return {
            "status": "success",
            "message": f"Document {s3_path} deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete document: {str(e)}"
        )
