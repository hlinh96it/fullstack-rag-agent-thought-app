from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from bson import ObjectId

from src.dependencies import AWSDependency


s3_router = APIRouter(tags=["s3_router"])


@s3_router.get(
    "/{user_id}",
    description="Get all uploaded file in S3",
    response_model=Dict[int, Dict[str, Any]],
)
async def get_all_files(user_id: str, aws_client: AWSDependency):
    uploaded_files = {}

    try:
        response = aws_client.s3_client.list_objects_v2(
            Bucket=aws_client.settings.bucket_name, Prefix=f"{user_id}/"
        )

        if "Contents" in response:
            for idx, uploaded_file in enumerate(response["Contents"]):
                # Skip the folder object itself (ends with /)
                if uploaded_file["Key"].endswith("/"):
                    continue

                metadata = {
                    "Title": uploaded_file["Key"],
                    "Size": uploaded_file["Size"] / 1024,
                    "Uploaded date": uploaded_file["LastModified"],
                }
                uploaded_files[idx] = metadata
            return uploaded_files
        else:
            return {}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get uploaded files: {str(e)}"
        )


@s3_router.post(
    "/upload/{user_id}",
    description="Upload files to S3 storage",
    response_model=Dict[str, Any],
)
async def upload_files(
    user_id: str, aws_client: AWSDependency, files: List[UploadFile] = File(...)
) -> Dict[str, Any]:
    """
    Upload multiple files to S3 bucket under user's folder.
    Supports PDF and image files (PNG, JPG, JPEG, GIF, WEBP).
    Maximum 5 files, each up to 5MB.
    """

    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files allowed")

    uploaded_files = []
    failed_files = []

    try:
        for file in files:
            try:
                content = await file.read()
                file_size = len(content)

                if file_size > 10 * 1024 * 1024:
                    failed_files.append(
                        {"filename": file.filename, "error": "File size exceeds 10MB"}
                    )
                    continue
                elif file_size < 1024:
                    failed_files.append(
                        {
                            "filename": file.filename,
                            "error": "File size smaller than 1MB",
                        }
                    )
                    continue

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                s3_key = f"{user_id}/{str(ObjectId())}.pdf"

                aws_client.s3_client.put_object(
                    Bucket=aws_client.bucket_name,
                    Key=s3_key,
                    Body=content,
                    ContentType=file.content_type,
                    Metadata={
                        "original_filename": file.filename,
                        "uploaded_by": user_id,
                        "uploaded_timestamp": timestamp,
                    },
                )
                uploaded_files.append(
                    {
                        "original_filename": file.filename,
                        "s3_key": s3_key,
                        "size": file_size,
                        "content_type": file.content_type,
                    }
                )

            except Exception as e:
                failed_files.append(
                    {"filename": file.filename, "error": f"Upload failed: {str(e)}"}
                )
        return {
            "uploaded": len(uploaded_files),
            "failed": len(failed_files),
            "uploaded_files": uploaded_files,
            "failed_files": failed_files,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")


@s3_router.get(
    "/download/{user_id}/{file_key:path}", description="Download file from S3"
)
async def download_file(
    user_id: str, file_key: str, aws_client: AWSDependency
) -> StreamingResponse:
    try:
        response = aws_client.s3_client.get_object(
            Bucket=aws_client.bucket_name, Key=f"{user_id}/{file_key}"
        )

        # Get the original filename from metadata, fallback to file_key
        original_filename = response.get("Metadata", {}).get(
            "original_filename", file_key.split("/")[-1]
        )

        # Use ContentType from response, default to application/pdf since we're storing PDFs
        content_type = response.get("ContentType", "application/pdf")

        return StreamingResponse(
            response["Body"].iter_chunks(),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{original_filename}"'
            },
        )

    except aws_client.s3_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download file: {str(e)}"
        )


@s3_router.delete(
    "/delete/{user_id}/{file_key:path}",
    description="Delete a file from S3 storage",
    response_model=Dict[str, Any],
)
async def delete_file(
    user_id: str, file_key: str, aws_client: AWSDependency
) -> Dict[str, Any]:
    """
    Delete a file from S3 bucket.
    """
    try:
        # Construct the full S3 key
        full_s3_key = f"{user_id}/{file_key}"

        # Delete the file from S3
        aws_client.s3_client.delete_object(
            Bucket=aws_client.bucket_name, Key=full_s3_key
        )

        return {
            "status": "success",
            "message": f"File {full_s3_key} deleted successfully",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
