![GitHub contributors](https://img.shields.io/github/contributors/AkaruiYami/syFinance)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/AkaruiYami/syFinance)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues-pr/AkaruiYami/syFinance)


# 🛠️ Contributing to syFinance

Thank you for your interest in contributing to **syFinance**, a personal finance dashboard built with Streamlit. We welcome contributions that improve functionality, fix bugs, enhance UI/UX, or expand documentation. This is my small project that was started because I want to track my transaction and I don't want to use excel. :)

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Code Style Guidelines](#code-style-guidelines)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)
- [License](#license)

## 🚀 Getting Started

1. **Fork the repository**  
   Click the "Fork" button at the top right of this repo to create your own copy.

2. **Clone your fork**  

   ```bash
   git clone https://github.com/<your-username>/syFinance.git
   cd syFinance
   ```

3. **Install dependencies**  
   Make sure you have Python 3.13+ and Streamlit installed.  

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**  

   ```bash
   uv run streamlit run main.py
   ```

   On first launch, the app will prompt you to create an admin account.
   No database setup step is required — the app bootstraps everything automatically.

## ✨ How to Contribute

- **Bug Fixes:** Submit a pull request with a clear description of the issue and your fix.
- **New Features or Major Changes:** **Please open an issue first** to discuss your idea before submitting a pull request. This helps avoid duplicated effort and ensures alignment with the project goals.
- **Documentation:** Help improve the README or add usage examples.
- **Refactoring:** Clean up code, improve performance, or enhance readability.

## 🧼 Code Style Guidelines

- Follow [PEP8](https://pep8.org/) for Python code.
- Use [ruff](https://docs.astral.sh/ruff/) for linting and autoformatting (recommended):

  ```bash
  pip install ruff
  ruff check . --fix
  ```

- Use meaningful variable and function names.
- Keep functions modular and well-documented.
- Include comments for complex logic.

## 🐞 Reporting Issues

If you find a bug, please:

- Check if it’s already reported.
- Include steps to reproduce the issue.
- Share screenshots or logs if possible.

## 💡 Feature Requests

Have an idea to improve syFinance?  
Open an issue with the **Feature Request** label and describe:

- What the feature does
- Why it’s useful
- Any implementation suggestions

## 📄 License

This project is licensed under the MIT License. See [LICENSE](/LICENSE) for details.
