from datetime import date

import pytest

import app as app_module


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        self.conn.queries.append((sql, params))

    def fetchall(self):
        return self.conn.rows

    def fetchone(self):
        return self.conn.rows[0] if self.conn.rows else None


class FakeConnection:
    def __init__(self):
        self.queries = []
        self.rows = []
        self.commits = 0
        self.closed = False

    def cursor(self, dictionary=False):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


@pytest.fixture
def db(monkeypatch):
    conn = FakeConnection()
    monkeypatch.setattr(app_module.mysql.connector, 'connect', lambda **kwargs: conn)
    return conn


@pytest.fixture
def client(db):
    app_module.app.config['TESTING'] = True
    return app_module.app.test_client()


def make_task(**overrides):
    task = {'id': 1, 'task': 'Write report', 'status': False, 'due_date': None, 'priority': 'medium'}
    task.update(overrides)
    return task


def test_index_lists_tasks(client, db):
    db.rows = [make_task(due_date=date(2030, 1, 2), priority='high')]
    response = client.get('/')
    assert response.status_code == 200
    assert b'Write report' in response.data
    assert b'High' in response.data
    assert b'Due Wed 02 Jan 2030' in response.data
    assert db.closed


def test_index_empty(client, db):
    response = client.get('/')
    assert b'No tasks yet.' in response.data


def test_add_task(client, db):
    response = client.post('/add', data={'task': '  Buy milk ', 'priority': 'low', 'due_date': '2030-05-01'})
    assert response.status_code == 302
    sql, params = db.queries[-1]
    assert sql.startswith('INSERT INTO tasks')
    assert params == ('Buy milk', False, 'low', '2030-05-01')
    assert db.commits == 1


def test_add_task_without_due_date(client, db):
    client.post('/add', data={'task': 'Buy milk', 'priority': 'medium', 'due_date': ''})
    assert db.queries[-1][1] == ('Buy milk', False, 'medium', None)


@pytest.mark.parametrize('data', [
    {'task': '   '},
    {'task': 'x' * 256},
    {'task': 'ok', 'priority': 'urgent'},
    {'task': 'ok', 'due_date': 'tomorrow'},
])
def test_add_task_rejects_bad_input(client, db, data):
    response = client.post('/add', data=data)
    assert response.status_code == 400
    assert db.commits == 0


def test_toggle_task(client, db):
    response = client.post('/toggle/3')
    assert response.status_code == 302
    assert db.queries[-1] == ('UPDATE tasks SET status = NOT status WHERE id = %s', (3,))
    assert db.commits == 1


def test_delete_task(client, db):
    response = client.post('/delete/7')
    assert response.status_code == 302
    assert db.queries[-1] == ('DELETE FROM tasks WHERE id = %s', (7,))
    assert db.commits == 1


def test_delete_requires_post(client, db):
    assert client.get('/delete/7').status_code == 405
    assert db.queries == []


def test_edit_form_shows_task(client, db):
    db.rows = [make_task(due_date=date(2030, 1, 2), priority='low')]
    response = client.get('/edit/1')
    assert response.status_code == 200
    assert b'value="Write report"' in response.data
    assert b'value="2030-01-02"' in response.data
    assert b'<option value="low" selected>' in response.data


def test_edit_missing_task(client, db):
    assert client.get('/edit/99').status_code == 404
    assert client.post('/edit/99', data={'task': 'x'}).status_code == 404


def test_edit_updates_task(client, db):
    db.rows = [make_task()]
    response = client.post('/edit/1', data={'task': 'Write final report', 'priority': 'high', 'due_date': ''})
    assert response.status_code == 302
    sql, params = db.queries[-1]
    assert sql.startswith('UPDATE tasks SET task')
    assert params == ('Write final report', 'high', None, 1)
    assert db.commits == 1


def test_init_db_adds_missing_columns(db):
    db.rows = [('id',), ('task',), ('status',)]
    app_module.init_db()
    sql = [q for q, _ in db.queries]
    assert 'ALTER TABLE tasks ADD COLUMN due_date DATE NULL' in sql
    assert any(q.startswith('ALTER TABLE tasks ADD COLUMN priority') for q in sql)
    assert db.commits == 1
