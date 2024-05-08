from typing import Any, Dict
import unicodedata
import re
from slugify import slugify


# Function to generate a slug from a name
def generate_slug(name:str) -> str:
    # # Normalize the string to remove diacritics (accents, etc.)
    # name = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("ASCII")
    # # Convert to lowercase, replace spaces with hyphens, and remove invalid characters
    # slug = re.sub(r"[^\w\s-]", "", name).strip().lower()
    # slug = re.sub(r"\s+", "-", slug)  # Replace spaces with hyphens
    slug=slugify(name)
    return slug
