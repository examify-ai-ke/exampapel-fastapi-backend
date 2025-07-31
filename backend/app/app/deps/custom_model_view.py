from starlette_admin.contrib.sqla import ModelView
from starlette.requests import Request


class CustomModelView(ModelView):
    async def list(self, request: Request):
        request.scope["root_path"] = (
            "/api/v1"  # Set the root path for Starlette-Admin's internal API
        )
        return await super().list(request)
