from app.models.group_model import Group
from app.models.user_model import User
from app.schemas.group_schema import IGroupCreate, IGroupUpdate
from app.crud.base_crud import CRUDBase
from app.utils.exceptions.common_exception import IdNotFoundException
from sqlmodel import select, func
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException


class CRUDGroup(CRUDBase[Group, IGroupCreate, IGroupUpdate]):
    async def get_group_by_name(
        self, *, name: str, db_session: AsyncSession | None = None
    ) -> Group:
        db_session = db_session or super().get_db().session
        group = await db_session.execute(select(Group).where(Group.name == name))
        return group.scalar_one_or_none()

    async def add_user_to_group(self, *, user: User, group_id: UUID) -> Group:
        db_session = super().get_db().session
        group = await super().get(id=group_id)
        group.users.append(user)
        db_session.add(group)
        await db_session.commit()
        await db_session.refresh(group)
        return group

    async def add_users_to_group(
        self,
        *,
        users: list[User],
        group_id: UUID,
        db_session: AsyncSession | None = None,
    ) -> Group:
        db_session = db_session or super().get_db().session
        group = await super().get(id=group_id, db_session=db_session)
        group.users.extend(users)
        db_session.add(group)
        await db_session.commit()
        await db_session.refresh(group)
        return group

    async def remove_user_from_group(self, user: User, group_id: UUID) -> Group:
        """
        Remove a user from a group
        """
        group = await self.get(id=group_id)
        if not group:
            raise IdNotFoundException(Group, id=group_id)
        
        # Check if user is in the group
        if user not in group.users:
            raise HTTPException(
                status_code=400,
                detail=f"User {user.email} is not in group {group.name}"
            )
        
        # Remove user from group
        group.users.remove(user)
        
        # Save changes
        await self.db_session.commit()
        await self.db_session.refresh(group)
        return group

    async def count_users_in_group(
        self, 
        *, 
        group_id: UUID, 
        db_session: AsyncSession | None = None
    ) -> int:
        """
        Count the number of users in a specific group
        """
        db_session = db_session or self.db.session
        
        # Query the UserGroup link table directly for better performance
        from app.models.user_model import UserGroup
        query = select(func.count(UserGroup.user_id)).where(UserGroup.group_id == group_id)
        result = await db_session.execute(query)
        return result.scalar_one() or 0


group = CRUDGroup(Group)
