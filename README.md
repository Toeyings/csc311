# Task For The Week

A small Flask + MySQL to-do list. You can add tasks with a priority and an optional due date, mark them done, edit them and delete them.

## Requirements

- Python 3.9+
- A running MySQL (or MariaDB) server

## Setup

1. **Create the database and a user** (in the MySQL shell, as an admin user):

   ```sql
   CREATE DATABASE taskdb;
   CREATE USER 'ty'@'localhost' IDENTIFIED BY 'choose-a-password';
   GRANT ALL PRIVILEGES ON taskdb.* TO 'ty'@'localhost';
   ```

2. **Install the Python dependencies** in a virtual environment:

   ```bash
   python -m venv .venv
   # Windows:   .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure the connection.** Copy `.env.example` to `.env` and fill in your values:

   | Variable      | Default     |
   |---------------|-------------|
   | `DB_HOST`     | `localhost` |
   | `DB_USER`     | `root`      |
   | `DB_PASSWORD` | *(empty)*   |
   | `DB_NAME`     | `taskdb`    |
   | `FLASK_DEBUG` | `0`         |

   `.env` is git-ignored. Never commit real passwords.

## Running

```bash
python app.py
```

Then open http://127.0.0.1:5000. Starting the app creates the `tasks` table. If you have a table from an older version, the startup step also adds any missing columns. You can do this step on its own with `flask --app app init-db`.

## Tests

The tests replace the database with a fake connection, so they don't need MySQL:

```bash
pip install -r requirements-dev.txt
pytest
```

## Contributing

1. Fork the repo and create a branch from `main`.
2. Make your change and add or update tests in `tests/`.
3. Run `pytest` and make sure everything passes.
4. Open a pull request describing what you changed and why.
