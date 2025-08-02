from app.schemas.auth_schema import PasswordChange
from pydantic import ValidationError

# Test weak password
try:
    weak_password = PasswordChange(current_password="admin123", new_password="weak")
    print("❌ Weak password validation failed - should have been rejected")
except ValidationError as e:
    print("✅ Weak password correctly rejected:")
    for error in e.errors():
        print(f"   - {error['msg']}")

# Test strong password
try:
    strong_password = PasswordChange(current_password="admin123", new_password="StrongPass123!")
    print("✅ Strong password correctly accepted")
except ValidationError as e:
    print("❌ Strong password incorrectly rejected:")
    for error in e.errors():
        print(f"   - {error['msg']}")

# Test sequential patterns
try:
    sequential_password = PasswordChange(current_password="admin123", new_password="Password123!")
    print("✅ Sequential pattern test passed")
except ValidationError as e:
    print("✅ Sequential pattern correctly rejected:")
    for error in e.errors():
        print(f"   - {error['msg']}")
