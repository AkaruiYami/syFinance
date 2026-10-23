import streamlit as st
from argon2 import PasswordHasher

from models.income import Income
from models.transaction import Transactions
from models.user import User
from models.wishlist import Wishlist


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


def get_user(user_id: int):
    user = User.objects().filter(id=user_id).first()
    if not user:
        raise ValueError("User not found.")
    return user


def create_user(name, password, email, description, role="user"):
    ph = PasswordHasher()

    new_user_data = {}
    new_user_data["name"] = name.strip()
    new_user_data["password"] = ph.hash(password)
    new_user_data["email"] = email.strip() if email else ""
    new_user_data["description"] = description.strip() if description else ""
    new_user_data["role"] = role.strip() if role else "user"
    user = User.new(**new_user_data)
    user.save()


def delete_user(user_id: int):
    # Safety check: admin cannot delete themselves
    current_user_id = st.session_state.get("user_id")
    if current_user_id == user_id:
        raise ValueError("You cannot delete your own account.")

    user = get_user(user_id)

    # Cascade deletion: delete all related data first
    Transactions.objects().filter(user_id=user_id).delete()
    Income.objects().filter(user_id=user_id).delete()
    Wishlist.objects().filter(user_id=user_id).delete()

    # Then delete the user
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


def can_modify_user_role(target_user_id: int, new_role: str) -> bool:
    """Check if current user can modify the role of target user."""
    current_user_id = st.session_state.get("user_id")
    current_user_role = st.session_state.get("user_role")

    # Only admins can change roles
    if current_user_role != "admin":
        return False

    # Admin cannot change their own role to non-admin
    if current_user_id == target_user_id and new_role != "admin":
        return False

    return True


def update_user_role(user_id: int, new_role: str):
    """Update a user's role with safety checks."""
    if not can_modify_user_role(user_id, new_role):
        raise ValueError("You cannot modify this user's role.")

    user = get_user(user_id)
    user.role = new_role.strip()
    user.save()

    # Update session state if this is the current user
    current_user_id = st.session_state.get("user_id")
    if current_user_id == user_id:
        st.session_state.user_role = new_role


# ---------------------------------------------------------------------------
# Category CRUD
# ---------------------------------------------------------------------------

from models.category import Category
from models.subcategory import Subcategory


def get_categories():
    return Category.objects().all(order_by="name")


def create_category(name: str):
    name = name.strip()
    if not name:
        raise ValueError("Category name cannot be empty.")
    existing = Category.objects().filter(name=name).first()
    if existing:
        raise ValueError(f"Category '{name}' already exists.")
    cat = Category.new(name=name)
    cat.save()
    return cat


def update_category(category_id: int, new_name: str):
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Category name cannot be empty.")
    cat = Category.objects().filter(id=category_id).first()
    if not cat:
        raise ValueError("Category not found.")
    duplicate = Category.objects().filter(name=new_name).first()
    if duplicate and duplicate.id != category_id:
        raise ValueError(f"Category '{new_name}' already exists.")
    old_name = cat.name
    cat.name = new_name
    cat.save()
    return old_name


def delete_category(category_id: int):
    cat = Category.objects().filter(id=category_id).first()
    if not cat:
        raise ValueError("Category not found.")
    count = get_category_usage_count(cat.name)
    if count > 0:
        raise ValueError(
            f"Cannot delete '{cat.name}': {count} transaction(s) still use this category."
        )
    Subcategory.objects().filter(category_id=category_id).delete()
    cat.delete()
    cat.save()


def get_category_usage_count(category_name: str) -> int:
    rows = (
        Transactions.objects().filter(category=category_name).all()
    )
    return len(rows)


# ---------------------------------------------------------------------------
# Subcategory CRUD
# ---------------------------------------------------------------------------


def get_subcategories(category_id: int):
    return Subcategory.objects().filter(category_id=category_id).all(order_by="name")


def create_subcategory(name: str, category_id: int):
    name = name.strip()
    if not name:
        raise ValueError("Subcategory name cannot be empty.")
    cat = Category.objects().filter(id=category_id).first()
    if not cat:
        raise ValueError("Parent category not found.")
    existing = Subcategory.objects().filter(name=name, category_id=category_id).first()
    if existing:
        raise ValueError(f"Subcategory '{name}' already exists in '{cat.name}'.")
    sub = Subcategory.new(name=name, category=category_id)
    sub.save()
    return sub


def update_subcategory(sub_id: int, new_name: str):
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Subcategory name cannot be empty.")
    sub = Subcategory.objects().filter(id=sub_id).first()
    if not sub:
        raise ValueError("Subcategory not found.")
    duplicate = Subcategory.objects().filter(
        name=new_name, category_id=sub.category_id
    ).first()
    if duplicate and duplicate.id != sub_id:
        raise ValueError(f"Subcategory '{new_name}' already exists in this category.")
    sub.name = new_name
    sub.save()


def delete_subcategory(sub_id: int):
    sub = Subcategory.objects().filter(id=sub_id).first()
    if not sub:
        raise ValueError("Subcategory not found.")
    count = get_subcategory_usage_count(sub.name)
    if count > 0:
        raise ValueError(
            f"Cannot delete '{sub.name}': {count} transaction(s) still use this subcategory."
        )
    sub.delete()
    sub.save()


def get_subcategory_usage_count(subcategory_name: str) -> int:
    rows = (
        Transactions.objects().filter(subcategory=subcategory_name).all()
    )
    return len(rows)
