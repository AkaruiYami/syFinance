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
        print("Missing page_name aqgument.")
        print("Example usage:")
        print("`python manage.py new_page my_new_page_name`")
        return
    page_name = sys.argv[2]
    page_file = f"./pages/p_{page_name}.py"
    with open(page_file, "w") as f:
        title = page_name.replace("_", " ").title()
        template_str = f"""import streamlit as st

st.set_page_config(page_title="{title}", layout="wide")

st.title("{title}")
st.markdown("A simple {title} page.")
st.divider()
        """
        f.write(template_str)

    print(f"New file created -> [{page_file}]")


def init_db_wrapped():
    ph = PasswordHasher()

    new_username = input("Set Username [admin]: ") or "admin"
    new_pass = ph.hash(getpass.getpass(prompt="Set Password [admin]: ")) or ph.hash(
        "admin"
    )
    confirm_new_pass = getpass.getpass(prompt="Confirm Password [admin]: ") or "admin"
    if not ph.verify(new_pass, confirm_new_pass):
        print("Make sure the password enter are the same!")
        return
    print("Success setting up new account.")

    txt = ""
    with open(".env", "w") as file:
        txt += 'APP_NAME="Personal Finance Dashboard"\n'
        txt += 'DB_PATH="data/finance.db"\n'
        txt += 'CURRENCY="RM"\n'
        txt += f'USERNAME="{new_username}"\n'
        txt += f'PASSWORD="{new_pass}"\n'
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
