from models.user import User
from argon2 import PasswordHasher


def get_users(limit: int = 50):
    assert limit > 0 or limit == -1, "Limit must be 1 or more."
    if limit == -1:
        return User.objects().all()

    if limit == 1:
        user = User.objects().first()
        return [user] if user else []

    users = User.objects().all()  # NOTE: need to reconsider this
    users = users[:limit]
    return users


def get_user(user_id: int) -> User:
    user = User.objects().filter(id=user_id).first()
    if not user:
        raise ValueError("User not found.")
    return user


def create_user(name, password, email, description):
    ph = PasswordHasher()

    new_user_data = {}
    new_user_data["name"] = name.strip()
    new_user_data["password"] = ph.hash(password)
    new_user_data["email"] = email.strip()
    new_user_data["description"] = description.strip()
    user = User.new(**new_user_data)
    user.save()


def delete_user(user_id: int):
    user = get_user(user_id)
    user.delete()
    user.save()


def cancel_delete_user(user_id: int):
    user = get_user(user_id)
    delattr(user, "_marked_for_deletion")


def validate_username_is_unique(name: str):
    users = get_users(limit=-1)
    for user in users:
        if user.name == name:
            return False
    return True


def is_username_valid(name: str):
    caseinsensitive_invalid = ["username", "admin", "name"]
    if name.lower() in caseinsensitive_invalid:
        return False
    return True


def create_new_password(password: str):
    ph = PasswordHasher()
    return ph.hash(password)
