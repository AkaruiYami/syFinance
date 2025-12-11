#!/usr/bin/env python3
import getpass
import os
import sys
from argon2 import PasswordHasher, exceptions as argon2_exceptions
from utils.db import init_db, migrate_db


# ---------------------------------------------
#   CUSTOM FUNCTIONS
# ---------------------------------------------
def create_new_page():
    if len(sys.argv) < 3:
        print("Missing page_name argument.")
        print("Example usage:")
        print("  python manage.py new_page my_new_page_name [require_login]")
        return

    page_name = sys.argv[2]
    require_login_arg = False
    if len(sys.argv) > 3:
        require_login_arg = str(sys.argv[3]).lower() in ("true", "1", "yes", "y")

    pages_dir = os.path.join(".", "pages")
    os.makedirs(pages_dir, exist_ok=True)

    page_file = os.path.join(pages_dir, f"p_{page_name}.py")
    title = page_name.replace("_", " ").title()

    # Base template
    template_lines = ["import streamlit as st", ""]

    # Optional require_login
    if require_login_arg:
        template_lines += [
            "from utils.auth import require_login",
            "",
            "require_login()",
            "",
        ]

    # Page content
    template_lines += [
        f'st.set_page_config(page_title="{title}", layout="wide")',
        "",
        f'st.title("{title}")',
        f'st.markdown("A simple {title} page.")',
        "st.divider()",
        "",
        "st.header('Page under construction!')",
    ]

    # If file exists, do not overwrite silently
    if os.path.exists(page_file):
        print(f"File already exists -> [{page_file}] (won't overwrite)")
        return

    with open(page_file, "w", encoding="utf-8") as f:
        f.write("\n".join(template_lines))

    print(f"New file created -> [{page_file}]")


def init_db_wrapped():
    ph = PasswordHasher()

    new_username = input("Set Username [admin]: ").strip() or "admin"

    # Prompt password (allow empty input to select default 'admin')
    raw_pass = getpass.getpass(prompt="Set Password [admin]: ").strip()
    if not raw_pass:
        raw_pass = "admin"

    confirm_raw = getpass.getpass(prompt="Confirm Password [admin]: ").strip()
    if not confirm_raw:
        confirm_raw = "admin"

    if raw_pass != confirm_raw:
        print("Passwords do not match — aborting.")
        return

    try:
        hashed = ph.hash(raw_pass)
    except Exception as e:
        print("Failed to hash password:", e)
        return

    print("Success setting up new account.")

    env_lines = [
        'APP_NAME="Personal Finance Dashboard"',
        'DB_PATH="data/finance.db"',
        'CURRENCY="RM"',
        f'APP_USERNAME="{new_username}"',
        f'APP_PASSWORD="{hashed}"',
    ]
    env_text = "\n".join(env_lines) + "\n"

    env_path = ".env"
    try:
        # Write with restrictive permissions (rw-------) where possible
        with open(env_path, "w", encoding="utf-8") as file:
            file.write(env_text)
        try:
            os.chmod(env_path, 0o600)
        except Exception:
            # chmod may fail on Windows or restricted FS — ignore but try
            pass
    except OSError as e:
        print(f"Failed to write {env_path}: {e}")
        return

    # Call your DB init routine
    try:
        init_db()
    except Exception as e:
        print("init_db() raised an exception:", e)
        return

    print(f"Initialized DB and wrote {env_path}.")


def migrate_db_wrapped():
    init_db(False)
    migrate_db()


def add_new_user():
    from models.user import User

    new_user_data = {}
    ph = PasswordHasher()

    new_user_data["name"] = input("Set Username [admin]: ").strip() or "admin"
    if User.objects().filter(name=new_user_data["name"]).first() is not None:
        print("User with given username already exist. Try other username instead.")
        return

    raw_pass = getpass.getpass(prompt="Set Password [admin]: ").strip()
    if not raw_pass:
        raw_pass = "admin"

    confirm_raw = getpass.getpass(prompt="Confirm Password [admin]: ").strip()
    if not confirm_raw:
        confirm_raw = "admin"

    if raw_pass != confirm_raw:
        print("Passwords do not match — aborting.")
        return

    try:
        new_user_data["password"] = ph.hash(raw_pass)
    except Exception as e:
        print("Failed to hash password:", e)
        return

    d = User.new(**new_user_data)
    d.save()

    print("Success setting up new account.")


# ---------------------------------------------
# COMMAND REGISTRY
# ---------------------------------------------
COMMANDS = {
    "init_db": init_db_wrapped,
    "migrate": migrate_db_wrapped,
    "new_page": create_new_page,
    "add_new_user": add_new_user,
}


# ---------------------------------------------
# ENTRY POINT
# ---------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python manage.py <command>")
        print("Available commands:")
        for name in COMMANDS.keys():
            print(f"  - {name}")
        sys.exit(1)

    command = sys.argv[1]

    if command not in COMMANDS:
        print(f"Unknown command: {command}")
        print("Available commands:")
        for name in COMMANDS:
            print(f"  - {name}")
        sys.exit(1)

    # Execute the command
    COMMANDS[command]()


if __name__ == "__main__":
    main()
