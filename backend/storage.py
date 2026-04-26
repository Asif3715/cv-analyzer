import uuid

import httpx

from backend.config import settings


def _headers() -> dict:
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing in .env")
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }


async def upload_pdf_to_supabase(file_bytes: bytes, original_filename: str) -> str:
    if not settings.supabase_project_url:
        raise RuntimeError("SUPABASE_PROJECT_URL missing in .env")

    bucket = settings.supabase_bucket_name
    object_name = f"uploads/{uuid.uuid4()}-{original_filename}"
    url = f"{settings.supabase_project_url}/storage/v1/object/{bucket}/{object_name}"

    headers = _headers()
    headers["Content-Type"] = "application/pdf"
    headers["x-upsert"] = "false"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, content=file_bytes)
        response.raise_for_status()

    return object_name
