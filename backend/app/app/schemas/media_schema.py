from app.models.media_model import MediaBase
from app.utils.partial import optional
from uuid import UUID
from pydantic import BaseModel, model_validator

class IMediaCreate(MediaBase):
    pass


# All these fields are optional
@optional()
class IMediaUpdate(MediaBase):
    pass


class IMediaRead(MediaBase):
    id: UUID | str
    link: str | None = None

    @model_validator(mode="before")
    @classmethod
    def clean_path(cls, values):
        # Clean path if it's a full URL (legacy data fix)
        # Handle dict or object
        if isinstance(values, dict):
            path = values.get("path")
        else:
            path = getattr(values, "path", None)
            
        if path and (path.startswith("http://") or path.startswith("https://")):
            try:
                from urllib.parse import urlparse, unquote
                parsed = urlparse(path)
                path_parts = parsed.path.lstrip("/").split("/")
                if len(path_parts) > 1:
                    clean_path = "/".join(path_parts[1:])
                else:
                    clean_path = path_parts[0]
                clean_path = unquote(clean_path)
                
                if isinstance(values, dict):
                    values["path"] = clean_path
                else:
                    # If it's an object, we can't easily modify it locally without side effects
                    # ensuring we return a dict is safer for pydantic v1 usually
                    # but for v2/compat sticking to dict update
                    pass # Pydantic from_attributes usually handles object access. 
                    # If we need to modify, we convert to dict.
                    values = values.__dict__.copy()
                    values["path"] = clean_path
            except Exception:
                pass
        return values


class IMediaReadForInstituion(BaseModel):
    id: UUID | str
    link: str | None = None
