#!/usr/bin/env python3
import getpass
from argon2 import PasswordHasher
import sys
from utils.db import init_db


# ---------------------------------------------
#   CUSTOM FUNCTIONS
# ---------------------------------------------
def create_new_page():
    if len(sys.argv) < 3:
        print("Missing page_name argument.")
        print("Example usage:")
        print("`python manage.py new_page my_new_page_name [require_login]`")
        return

    page_name = sys.argv[2]
    require_login_arg = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else False

    page_file = f"./pages/p_{page_name}.py"
    with open(page_file, "w") as f:
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

        f.write("\n".join(template_lines))

    print(f"New file created -> [{page_file}]")


def init_db_wrapped():
    ph = PasswordHasher()

    new_username = input("Set Username [admin]: ") or "admin"
    new_pass = ph.hash(
        getpass.getpass(prompt="Set Password [admin]: ").strip()
    ) or ph.hash("admin")
    confirm_new_pass = (
        getpass.getpass(prompt="Confirm Password [admin]: ").strip() or "admin"
    )
    if not ph.verify(new_pass, confirm_new_pass):
        print("Make sure the password enter are the same!")
        return
    print("Success setting up new account.")

    txt = ""
    with open(".env", "w") as file:
        txt += 'APP_NAME="Personal Finance Dashboard"\n'
        txt += 'DB_PATH="data/finance.db"\n'
        txt += 'CURRENCY="RM"\n'
        txt += f'APP_USERNAME="{new_username}"\n'
        txt += f'APP_PASSWORD="{new_pass}"\n'
        file.write(txt)

    init_db()


# ---------------------------------------------
# COMMAND REGISTRY
# ---------------------------------------------
# Map command names to functions
COMMANDS = {
    "init_db": init_db_wrapped,
    "new_page": create_new_page,
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
