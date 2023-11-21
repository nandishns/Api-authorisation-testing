import sqlite3
from flask import Flask, jsonify, request, g
from faker import Faker

app = Flask(__name__)
DATABASE = 'library.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        
        fake = Faker()
        for _ in range(50):
            title = fake.catch_phrase()
            author = fake.name()
            db.execute('INSERT INTO books (title, author) VALUES (?, ?)', (title, author))
        
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/books', methods=['GET'])
def get_books():
    books = query_db('SELECT * FROM books')
    return jsonify([{'id': book['id'], 'title': book['title'], 'author': book['author']} for book in books])

@app.route('/book', methods=['POST'])
def add_book_endpoint():
    data = request.json
    db = get_db()
    db.execute('INSERT INTO books (title, author) VALUES (?, ?)', (data['title'], data['author']))
    db.commit()
    return jsonify({'message': 'Book added'}), 201

@app.route('/book/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    data = request.json
    db = get_db()
    db.execute('UPDATE books SET title = ?, author = ? WHERE id = ?', (data['title'], data['author'], book_id))
    db.commit()
    return jsonify({'message': 'Book updated'})

@app.route('/book/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    db = get_db()
    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    return jsonify({'message': 'Book deleted'})

if __name__ == '__main__':
    init_db() 
    app.run(debug=True)
