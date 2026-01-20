from models.user import User
from argon2 import PasswordHasher


def get_users(limit=50):
    assert limit > 0, "Limit must be 1 or more."

    if limit == 1:
        user = User.objects().first()
        return [user] if user else []

    users = User.objects().all()
    users = users[:limit]
    return users


def create_user(name, password, email, description):
    ph = PasswordHasher()

    new_user_data = {}
    new_user_data["name"] = name.strip()
    new_user_data["password"] = ph.hash(password)
    new_user_data["email"] = email.strip()
    new_user_data["description"] = description.strip()
    User.new(**new_user_data)
