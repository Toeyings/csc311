import os
from datetime import date

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, g, abort
import mysql.connector

#load settings from a .env file if there is one
load_dotenv()

#database connection settings come from the environment, never from the code
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'taskdb'),
}

PRIORITIES = ('high', 'medium', 'low')

app = Flask(__name__)


#open one connection per request and reuse it for the rest of that request
def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


#create the table, and add any columns that older versions of the table are missing
def init_db():
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS tasks ("
        "id INT AUTO_INCREMENT PRIMARY KEY, "
        "task VARCHAR(255) NOT NULL, "
        "status BOOLEAN NOT NULL DEFAULT FALSE, "
        "due_date DATE NULL, "
        "priority VARCHAR(10) NOT NULL DEFAULT 'medium')"
    )
    cursor.execute(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tasks'"
    )
    columns = {row[0] for row in cursor.fetchall()}
    if 'due_date' not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN due_date DATE NULL")
    if 'priority' not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN priority VARCHAR(10) NOT NULL DEFAULT 'medium'")
    db.commit()
    db.close()


@app.cli.command('init-db')
def init_db_command():
    """Create or update the tasks table."""
    init_db()
    print('Database initialised.')


#read and validate the task fields shared by the add and edit forms
def read_task_form():
    task = request.form.get('task', '').strip()
    if not task or len(task) > 255:
        abort(400, 'Task must be between 1 and 255 characters.')

    priority = request.form.get('priority', 'medium')
    if priority not in PRIORITIES:
        abort(400, 'Unknown priority.')

    due_date = request.form.get('due_date', '').strip() or None
    if due_date is not None:
        try:
            date.fromisoformat(due_date)
        except ValueError:
            abort(400, 'Due date must be YYYY-MM-DD.')

    return task, priority, due_date


#create route for the homepage
@app.route('/')
def index():
    cursor = get_db().cursor(dictionary=True)
    #unfinished tasks first, then by due date (no date last), then by priority
    cursor.execute(
        "SELECT * FROM tasks "
        "ORDER BY status, due_date IS NULL, due_date, FIELD(priority, 'high', 'medium', 'low'), id"
    )
    tasks = cursor.fetchall()
    return render_template('index.html', tasks=tasks, priorities=PRIORITIES, today=date.today())


# Route for adding a new task
@app.route('/add', methods=['POST'])
def add():
    task, priority, due_date = read_task_form()
    db = get_db()
    db.cursor().execute(
        "INSERT INTO tasks (task, status, priority, due_date) VALUES (%s, %s, %s, %s)",
        (task, False, priority, due_date),
    )
    db.commit()
    return redirect(url_for('index'))


# Route for marking a task done / not done
@app.route('/toggle/<int:task_id>', methods=['POST'])
def toggle(task_id):
    db = get_db()
    db.cursor().execute("UPDATE tasks SET status = NOT status WHERE id = %s", (task_id,))
    db.commit()
    return redirect(url_for('index'))


# Route for editing a task
@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
def edit(task_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    existing = cursor.fetchone()
    if existing is None:
        abort(404)

    if request.method == 'POST':
        task, priority, due_date = read_task_form()
        cursor.execute(
            "UPDATE tasks SET task = %s, priority = %s, due_date = %s WHERE id = %s",
            (task, priority, due_date, task_id),
        )
        db.commit()
        return redirect(url_for('index'))

    return render_template('edit.html', task=existing, priorities=PRIORITIES)


# Route for deleting a task (POST so links and prefetching can't delete anything)
@app.route('/delete/<int:task_id>', methods=['POST'])
def delete(task_id):
    db = get_db()
    db.cursor().execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    db.commit()
    return redirect(url_for('index'))


# Run the Flask application
if __name__ == '__main__':
    init_db()
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
