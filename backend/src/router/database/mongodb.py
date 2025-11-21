from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body, File, UploadFile, BackgroundTasks
from bson import ObjectId
import tempfile
import os
from pathlib import Path
from datetime import datetime

from src.schema.document.models import Document, ParsedDocument
from src.schema.user.models import User
from src.dependencies import MongoDependency, ParserDependency, AWSDependency, MilvusDependency

import logging
logger = logging.getLogger(__name__)


doc_router = APIRouter(tags=["doc_router"])


@doc_router.get(
    "/{user_id}",
    description="Get all documents (excluding doc_content for faster loading)",
    response_model=List[Document],
    response_model_by_alias=False,
)
async def get_all_docs(user_id: str, mongo_client: MongoDependency) -> List[Document]:
    try:
        # Use projection to exclude the large doc_content field from chunk_data
        # This significantly reduces payload size and improves performance
        response = await mongo_client.collection.find_one(
            {"_id": ObjectId(user_id)},
            {
                "_id": 1,
                "name": 1,
                "chat_list": 1,
                "doc_list._id": 1,
                "doc_list.s3_path": 1,
                "doc_list.title": 1,
                "doc_list.size": 1,
                "doc_list.uploaded_date": 1,
                "doc_list.indexed": 1,
                "doc_list.chunked": 1,
                "doc_list.chunk_error": 1,
                # Exclude doc_list.chunk_data entirely for maximum performance
            },
        )

        if response:
            response["_id"] = str(response["_id"])
            user_data = User(**response)

            # Simply return the documents as-is
            # The background task will update chunked status when complete
            # No need for additional queries here - trust the stored status
            return user_data.doc_list
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        logger.error(f"Error in get_all_docs: {e}")
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


@doc_router.get(
    "/{user_id}/{doc_id}",
    description="Get full document details",
    response_model=Document,
    response_model_by_alias=False,
)
async def get_document_detail(
    user_id: str, doc_id: str, mongo_client: MongoDependency
) -> Document:
    """
    Fetch complete document data including the full doc_content.
    Use this endpoint when you need to access the parsed content.
    """
    try:
        # Find the user and extract the specific document
        response = await mongo_client.collection.find_one(
            {"_id": ObjectId(user_id), "doc_list._id": ObjectId(doc_id)},
            {"doc_list.$": 1},  # Only return the matching document
        )

        if not response or "doc_list" not in response or len(response["doc_list"]) == 0:
            raise HTTPException(status_code=404, detail="Document not found")

        doc = response["doc_list"][0]
        doc["_id"] = str(doc["_id"])
        return Document(**doc)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get document details: {e}"
        )


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


async def chunk_index_documents(
    user_id: str, doc_id: ObjectId, temp_file_path: str,
    mongo_client: MongoDependency, parser_service: ParserDependency, milvus_client: MilvusDependency
):
    """
    Background task to parse document and update MongoDB with chunk data.
    """
    try:
        logger.info(f"Starting background chunking for document {doc_id}")

        # Parse the document
        parsed_docs = await parser_service.parse_document_langchain(temp_file_path)

        # Update the document in MongoDB with parsed data
        await mongo_client.collection.update_one(
            {"_id": ObjectId(user_id), "doc_list._id": doc_id},
            {"$set": {"doc_list.$.chunked": True}},
        )

        logger.info(
            f"Successfully completed chunking for document {doc_id}. "
            f"Sections: {len(parsed_docs) if parsed_docs else 0}"
        )

        logger.info(f"Start to indexing for document {doc_id}")
        indexed_docs = await milvus_client.index_document(parsed_docs)
        await mongo_client.collection.update_one(
            {"_id": ObjectId(user_id), "doc_list._id": doc_id},
            {"$set": {"doc_list.$.indexed": True}},
        )
        logger.info(
            f"Successfully completed indexing for document {doc_id} with {len(indexed_docs)}"
        )

    except Exception as e:
        logger.error(f"Failed to chunk document {doc_id}: {e}")
        # Update the document to indicate chunking failed
        await mongo_client.collection.update_one(
            {"_id": ObjectId(user_id), "doc_list._id": doc_id},
            {
                "$set": {
                    "doc_list.$.chunked": False, "doc_list.$.chunk_error": str(e),
                    "doc_list.$.indexed": False, "doc_list.$.indexed_error": str(e),
                }
            },
        )
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to delete temporary file {temp_file_path}: {e}")


@doc_router.post(
    "/upload/{user_id}",
    description="Upload file to S3 and save to MongoDB. Chunking happens in background.",
    response_model=Dict[str, Any],
)
async def upload_and_parse_document(
    user_id: str, background_tasks: BackgroundTasks,
    mongo_client: MongoDependency, aws_client: AWSDependency, parser_service: ParserDependency,
    milvus_client: MilvusDependency, file: UploadFile = File(...),
) -> Dict[str, Any]:
    """
    Upload a PDF file and return immediately:
    1. Upload to S3
    2. Save document metadata to MongoDB with chunked=False
    3. Start chunking in background (will update chunked=True when done)

    The client can poll to check when chunking is complete.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files are supported")

    # Read file content once
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB")
    elif file_size < 1024:
        raise HTTPException(
            status_code=400, detail="File size must be at least 1KB")

    try:
        # Generate unique identifiers
        doc_id = ObjectId()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{user_id}/{str(doc_id)}.pdf"

        # Upload to S3 (fast operation)
        aws_client.s3_client.put_object(
            Bucket=aws_client.bucket_name,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type or "application/pdf",
            Metadata={
                "original_filename": file.filename,
                "uploaded_by": user_id,
                "uploaded_timestamp": timestamp,
            },
        )

        # Create document object WITHOUT parsed data (will be added by background task)
        new_doc = {
            "_id": doc_id,
            "s3_path": s3_key,
            "title": file.filename,
            "size": round(file_size / 1024, 2),  # KB
            "uploaded_date": int(datetime.now().timestamp()),
            "indexed": False,
            "chunked": False,  # Will be set to True when chunk_data is added by background task
        }

        # Save to MongoDB
        await mongo_client.collection.find_one_and_update(
            filter={"_id": ObjectId(user_id)},
            update={"$push": {"doc_list": new_doc}},
        )

        # Create temporary file for background parsing
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(content)
        temp_file.close()
        temp_file_path = temp_file.name

        # Start chunking in background
        background_tasks.add_task(
            chunk_index_documents, user_id, doc_id, temp_file_path, mongo_client, parser_service,
            milvus_client
        )

        # Convert ObjectId to string for response
        new_doc["_id"] = str(new_doc["_id"])

        logger.info(
            f"Document {doc_id} uploaded. Chunking started in background.")

        return {
            "status": "success",
            "message": "File uploaded successfully. Chunking in progress...",
            "document": new_doc,
            "chunking_status": "processing",  # Frontend will poll for updates
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process document: {str(e)}"
        )
