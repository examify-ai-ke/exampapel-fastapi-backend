from app.models.base_uuid_model import BaseUUIDModel
from pydantic import computed_field
from sqlmodel import SQLModel
from app.utils.minio_client import S3Client, MinioClient
from app.core.config import settings
from app import api


class MediaBase(SQLModel):
    title: str | None = None
    description: str | None = None
    path: str | None = None


class Media(BaseUUIDModel, MediaBase, table=True):
    @computed_field
    @property
    def link(self) -> str | None:
        """Generate fresh pre-signed URL every time this property is accessed"""
        if self.path is None:
            return ""
        try:
            minio: MinioClient = api.deps.minio_auth()
            # Generate URL that expires in 7 days (refreshed on each request)
            url = minio.presigned_get_object(
                bucket_name=settings.S3_BUCKET_NAME, 
                object_name=self.path,
                expires_hours=168
            )
            return url
        except Exception:
            return self.path
