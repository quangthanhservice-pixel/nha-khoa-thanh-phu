import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=False)
import cloudinary
import cloudinary.uploader


def configure_cloudinary():
    url = os.getenv("CLOUDINARY_URL", "").strip()

    if not url:
        raise RuntimeError("Chưa cấu hình CLOUDINARY_URL")

    from urllib.parse import urlparse, unquote

    parsed = urlparse(url)

    if (
        parsed.scheme != "cloudinary"
        or not parsed.hostname
        or not parsed.username
        or not parsed.password
    ):
        raise RuntimeError("CLOUDINARY_URL không hợp lệ")

    cloudinary.config(
        cloud_name=parsed.hostname,
        api_key=unquote(parsed.username),
        api_secret=unquote(parsed.password),
        secure=True
    )


def upload_customer_avatar(file_data):
    configure_cloudinary()

    result = cloudinary.uploader.upload(
        file_data,
        folder="nha-khoa-thanh-phu/customer-reviews",
        resource_type="image",
        overwrite=False
    )

    return result["secure_url"], result["public_id"]


def delete_customer_avatar(public_id):
    configure_cloudinary()

    return cloudinary.uploader.destroy(
        public_id,
        resource_type="image"
    )


# CUSTOMER AVATAR VALIDATION V1
MAX_AVATAR_BYTES = 5 * 1024 * 1024


def upload_validated_customer_avatar(data, filename=""):
    from fastapi import HTTPException
    from io import BytesIO

    if not data:
        raise HTTPException(400, "Bạn chưa chọn ảnh")

    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(400, "Ảnh không được vượt quá 5 MB")

    signatures = (
        data.startswith(bytes.fromhex("FFD8FF")),
        data.startswith(bytes.fromhex("89504E470D0A1A0A")),
        data.startswith(b"RIFF")
        and data[8:12] == b"WEBP",
    )

    if not any(signatures):
        raise HTTPException(
            400, "Chỉ hỗ trợ ảnh JPG, PNG hoặc WebP"
        )

    try:
        return upload_customer_avatar(BytesIO(data))
    except Exception:
        raise HTTPException(
            502, "Không thể tải ảnh lên Cloudinary"
        )
