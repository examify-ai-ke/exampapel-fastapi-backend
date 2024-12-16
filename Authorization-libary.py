from authority import Permission, PermissionType
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class User:
    id: int
    username: str
    roles: List[str]


class ResourcePermission(Permission):
    """
    Flexible and intuitive permission management
    """

    def __init__(
        self,
        resource_type: str,
        allowed_roles: List[str] = None,
        owner_can_edit: bool = True,
    ):
        """
        Configure permissions for a specific resource type

        :param resource_type: Type of resource (e.g., 'hero', 'project')
        :param allowed_roles: Roles that can perform actions
        :param owner_can_edit: Whether resource owners can edit their resources
        """
        self.resource_type = resource_type
        self.allowed_roles = allowed_roles or ["admin"]
        self.owner_can_edit = owner_can_edit

    def can_view(self, user: User, resource_owner_id: Optional[int] = None) -> bool:
        """Check if user can view the resource"""
        return any(role in self.allowed_roles for role in user.roles) or (
            self.owner_can_edit and user.id == resource_owner_id
        )

    def can_edit(self, user: User, resource_owner_id: Optional[int] = None) -> bool:
        """Check if user can edit the resource"""
        return "admin" in user.roles or (
            self.owner_can_edit and user.id == resource_owner_id
        )

    def can_create(self, user: User) -> bool:
        """Check if user can create a resource"""
        return any(role in self.allowed_roles for role in user.roles)


# Example usage
hero_permissions = ResourcePermission(
    resource_type="hero", allowed_roles=["admin", "manager"], owner_can_edit=True
)


# Authorization check example
def create_hero(current_user: User, hero_data: dict):
    if not hero_permissions.can_create(current_user):
        raise PermissionError("Not authorized to create heroes")

    # Proceed with hero creation


# API endpoint example
@app.post("/heroes")
def create_hero_endpoint(
    hero_data: HeroCreate, current_user: User = Depends(get_current_user)
):
    try:
        return create_hero(current_user, hero_data)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
