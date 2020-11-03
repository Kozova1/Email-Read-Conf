from flask import (
    Flask,
    send_file,
    g,
    render_template,
    request,
    make_response
)
import sqlite3
import uuid
from datetime import timezone, datetime
from typing import Union

hostname = 'http://127.0.0.1:5000'

app = Flask(__name__)

def gen_link(db, email: str):
    id = uuid.uuid4().hex
    db.execute(
        'insert into links (id, email, when_read, was_read, is_active) values (?, ?, ?, ?, ?)',
        (id, email, '', 0, 0)
    )
    db.commit()
    return id

def is_valid(db, id: str):
    cursor = db.execute('select * from links where id = ?', (id,))
    return len(cursor.fetchall()) != 0

def access(db, id: str):
    if is_valid(db, id):
        db.execute(
            'update links set when_read = ?, was_read = 1, is_active = 0 where id = ?',
            (datetime.now(timezone.utc).isoformat(), id)
        )
        db.commit()

def to_link(path, id):
    return f'{hostname}/{path}/{id}'

def del_link(db, id: str):
    db.execute('delete from links where id = ?', (id,))
    db.commit()

# def status_of(db, id: str) -> str:
#     res = db.execute('select * from links where id = ?', (id,)).fetchone()
#     return res.when_read if res.was_read == 1 else None

def is_active(db, id: str) -> bool:
    row = db.execute('select * from links where id = ?', (id,)).fetchone()
    if row is None:
        return False
    return row['is_active'] == 1

@app.route('/verification/<id>', methods=['GET'])
def verify(id):
    db = get_db()
    if is_valid(db, id):
        if is_active(db, id):
            access(db, id)
        res = make_response(send_file('./img/1px.png', mimetype='image/png'))
        res.headers['Content-Type'] = 'image/png'
        res.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        res.headers['Pragma'] = 'no-cache'
        return res
    print('invalid id')
    return render_template('error.html', error=f"wrong id: {id}")

@app.route('/gen', methods=['GET'])
def gen_page():
    return app.send_static_file('gen.html')

@app.route('/gen', methods=['POST'])
def gen():
    email = request.form.get('email', None)
    if email is None:
        return render_template('error.html', error="no email provided in request")
    id = gen_link(get_db(), email)
    return render_template(
        'gen.html',
        statuslink=to_link('status', id), 
        email=email,
        link=to_link('verification', id)
    )

@app.route('/activate', methods=['POST'])
def activate():
    id = request.form.get('id', None)
    db = get_db()
    if id is not None:
        db.execute('update links set is_active = 1 where id = ?', (id,))
        db.commit()
        return render_template('activate.html', id=id)
    return render_template('error.html', error="no id provided in request")
    

@app.route('/status/<id>')
def status(id):
    row = get_db().execute('select * from links where id = ?', (id,)).fetchone()
    if row is None:
        return render_template('error.html', error=f"no link with id \"{id}\" found")
    return render_template(
        'status.html',
        email=row['email'],
        was_read=('Yes' if row['was_read'] == 1 else 'No'),
        is_active=('Yes' if row['is_active'] == 1 else 'No'),
        when_read=row['when_read'],
        id=id,
        link=to_link('verification', id)
    )

@app.route('/del', methods=['POST'])
def delete():
    id = request.form.get('id', None)
    if id is None:
        return render_template('error.html', error="no id provided in request")
    del_link(get_db(), id)
    return render_template('del.html', id=id)

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            './links.db',
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

###############

def main():
    app.run()
    close_db()

if __name__=='__main__':
    main()
