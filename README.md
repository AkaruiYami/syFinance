[![License: MIT](https://cdn.prod.website-files.com/5e0f1144930a8bc8aace526c/65dd9eb5aaca434fac4f1c34_License-MIT-blue.svg)](/LICENSE)
![GitHub last commit](https://img.shields.io/github/last-commit/AkaruiYami/syFinance)

# A simple personal finance dashboard

This is a simple finance dashboard where user can monitor their transactions.
Good for looking over monthly budget.

---

![login-screen-ss](docs/_static/_preview/syfinance-login-ss.png)

![quick-preview-gif](docs/_static/_preview/syfinance-preview.gif)

---

# How to Run

## Quick Start

Option 1: Using `pip`

```bash
git clone https://github.com/AkaruiYami/syFinance.git
cd syFinance
pip install -r requirements.txt
python -m streamlit run main.py
```

Option 2: Using `uv` (recommended)

```bash
git clone https://github.com/AkaruiYami/syFinance.git
cd syFinance
uv sync
uv run streamlit run main.py
```

On first launch, you'll be prompted to create your admin account.
No database setup or environment file is required — the app bootstraps everything automatically.

> [!Note]
> If you are using linux just run `./run.sh` script to run the app.

## Optional: CLI Tools

`manage.py` provides optional commands for advanced use:

```bash
uv run manage.py init_db       # Create DB + first user from terminal
uv run manage.py add_new_user  # Add a user from terminal
uv run manage.py migrate       # Run schema migrations
```

---

## Dependencies

This project uses [Streamlit](https://streamlit.io), licensed under the Apache License 2.0.  
See [Streamlit License](https://github.com/streamlit/streamlit/blob/develop/LICENSE) for details.

This project also include [argon2-cffi](https://github.com/hynek/argon2-cffi), licensed under the MIT License.
See [argon2-cffi License](https://github.com/hynek/argon2-cffi?tab=MIT-1-ov-file) for details.

![GitHub contributors](https://img.shields.io/github/contributors/AkaruiYami/syFinance)
