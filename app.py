from flask import Flask, render_template, request, redirect
import mysql.connector

#configure our database connection
db = mysql.connector.connect(
    host ='localhost',
    user ='ty',
    password ='typwd2',
    database = 'taskdb'
)

app = Flask(__name__)
cursor =db.cursor()

#crate a table
cursor.execute("CREATE TABLE IF NOT EXISTS tasks (id INT AUTO_INCREMENT PRIMARY KEY, task VARCHAR(255), status BOOLEAN)")

#create route for the homepage
@app.route('/')
def index():
    cursor.execute("SELECT * FROM tasks")
    task = cursor.fetchall()
    return render_template ("index.html", tasks=task)


# Route for adding a new task
@app.route('/add', methods=['POST'])
def add():
    task = request.form['task']
    cursor.execute("INSERT INTO tasks (task, status) VALUES (%s, %s)", (task, False))
    db.commit()
    return redirect('/')

# Route for deleting a task
@app.route('/delete/<int:task_id>')
def delete(task_id):
    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    db.commit()
    return redirect('/')

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)
