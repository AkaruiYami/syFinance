#!/usr/bin/env python3

import sys
from utils.db import init_db


# ---------------------------------------------
# COMMAND REGISTRY
# ---------------------------------------------
# Map command names to functions
COMMANDS = {
    "init_db": init_db,
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
