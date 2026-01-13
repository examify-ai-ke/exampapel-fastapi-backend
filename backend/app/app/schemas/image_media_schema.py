from app.models.image_media_model import ImageMedia, ImageMediaBase
from app.models.media_model import Media
from pydantic import model_validator
from .media_schema import IMediaRead, IMediaReadForInstituion
from app.utils.partial import optional
from pydantic import BaseModel
from uuid import UUID

# Image Media
class IImageMediaCreate(ImageMediaBase):
    pass


# All these fields are optional
@optional()
class IImageMediaUpdate(ImageMediaBase):
    pass


# Reverting to nested structure because Frontend expects 'media' key for Institution logos.
# This ensures uniformity (User profile will also be nested).
class IImageMediaRead(BaseModel):
    media: IMediaRead | None

    class Config:
        from_attributes = True


# Todo make it compatible with pydantic v2
class IImageMediaReadCombined(ImageMediaBase):
    link: str | None

    @model_validator(mode="before")
    def combine_attributes(cls, values):
        link_fields = {"link": values.get("link", None)}
        if "media" in values:
            if isinstance(values["media"], Media) and values["media"].path is not None:
                link_fields = {"link": values["media"].link}

        image_media_fields = {
            k: v for k, v in values.items() if k in ImageMedia.__fields__
        }
        output = {**image_media_fields, **link_fields}
        return output
