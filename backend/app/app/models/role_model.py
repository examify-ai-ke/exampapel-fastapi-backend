from sqlmodel import SQLModel, Relationship
from app.models.base_uuid_model import BaseUUIDModel


class RoleBase(SQLModel):
    name: str
    description: str


class Role(BaseUUIDModel, RoleBase, table=True):
    users: list["User"] = Relationship(  # noqa: F821
        back_populates="role", sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    # Add a method to convert to dictionary
    def dict(self):
        """Convert Role model to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }