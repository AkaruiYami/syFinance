#!/usr/bin/env python3

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


# ---------------------------------------------
# COMMAND REGISTRY
# ---------------------------------------------
# Map command names to functions
COMMANDS = {
    "init_db": init_db,
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
