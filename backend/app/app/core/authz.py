from app.models.hero_model import Hero
from app.models.user_model import User
from app.models.institution_model import Institution
from app.models.faculty_model import Faculty
from oso import Oso  # (1)


oso = Oso()  # (2)

# load policies

# Register classes for authorization
oso.register_class(Hero)
oso.register_class(User)
oso.register_class(Institution)
oso.register_class(Faculty)
oso.load_files(["app/core/authz.polar"])

def is_authorized(actor: User, action: str, resource, **kwargs):
    return oso.is_allowed(actor=actor, action=action, resource=resource, **kwargs)
