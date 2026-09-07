"""
upload.py — File upload endpoints.

POST /upload/image  → uploads a reference image, returns a public URL
"""
import io
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class UploadResponse(BaseModel):
    url: str
    filename: str
    size_bytes: int


@router.post(
    "/image",
    response_model=UploadResponse,
    summary="Upload a reference image for video generation",
    response_description="Public URL of the uploaded image",
)
async def upload_image(file: UploadFile = File(..., description="Reference image file (JPEG, PNG, or WebP, max 5 MB)")):
    """
    Upload a reference image and receive a publicly-accessible URL.

    The URL can then be passed as `reference_image_url` in the
    `POST /generate/video` request body.

    **Accepted formats:** JPEG, PNG, WebP
    **Max file size:** 5 MB
    """
    settings = get_settings()

    # ── Validate content type ─────────────────────────────────────────────
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(
            "upload_rejected_content_type",
            content_type=file.content_type,
            filename=file.filename,
        )
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {file.content_type}. Accepted: JPEG, PNG, WebP.",
        )

    # ── Validate file extension ───────────────────────────────────────────
    filename = file.filename or "image"
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[1].lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        logger.warning(
            "upload_rejected_extension",
            extension=ext,
            filename=filename,
        )
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file extension: {ext}. Accepted: .jpg, .jpeg, .png, .webp.",
        )

    # ── Read and validate size ────────────────────────────────────────────
    contents = await file.read()
    size = len(contents)

    if size > MAX_FILE_SIZE:
        logger.warning(
            "upload_rejected_size",
            size_bytes=size,
            max_bytes=MAX_FILE_SIZE,
            filename=filename,
        )
        raise HTTPException(
            status_code=422,
            detail=f"File too large: {size / (1024 * 1024):.1f} MB. Maximum allowed: 5 MB.",
        )

    if size == 0:
        raise HTTPException(status_code=422, detail="Empty file.")

    logger.info(
        "upload_image_accepted",
        filename=filename,
        content_type=file.content_type,
        size_bytes=size,
    )

    # ── Upload to fal.ai CDN ─────────────────────────────────────────────
    if settings.mock_generation_apis:
        # In mock mode, return a placeholder URL
        mock_url = "https://fal.media/files/mock/reference-image-placeholder.jpg"
        logger.info("mock_upload_image", url=mock_url)
        return UploadResponse(url=mock_url, filename=filename, size_bytes=size)

    try:
        import fal_client

        # fal_client.upload expects a file-like object or bytes
        url = fal_client.upload(io.BytesIO(contents), content_type=file.content_type)
        logger.info("upload_image_success", url=url, filename=filename)
        return UploadResponse(url=url, filename=filename, size_bytes=size)
    except Exception as e:
        logger.error("upload_image_failed", error=str(e), filename=filename)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to upload image to CDN: {e}",
        )
