from flask import Flask, request, g, abort
from flask_restx import Api, Resource, fields
import sqlite3
from faker import Faker
import re
import uuid

app = Flask(__name__)
authorizations = {
    'Bearer Auth': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    }
}

api = Api(app, version='1.0', title='Library API', description='A simple Library API', authorizations=authorizations, security='Bearer Auth')
DATABASE = 'library.db'

# Define user permissions
user_permissions = {
    "admin":      {"read": True, "write": True, "guest_view": True},
    "user":       {"read": True, "write": False, "guest_view": True},
    "guest":      {"read": False, "write": False, "guest_view": True}
}

def verify_token(token):
    if re.match(r'^adm-[0-9a-fA-F-]+$', token):
        return 'admin'
    elif re.match(r'^usr-[0-9a-fA-F-]+$', token):
        return 'user'
    elif re.match(r'^oth-[0-9a-fA-F-]+$', token):
        return 'other'
    else:
        return None

def get_auth_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        abort(401)  # Unauthorized access

    return auth_header.split(None, 1)[1].strip()

def require_auth():
    token = get_auth_token()
    user_type = verify_token(token)
    if user_type is None:
        abort(403)  # Forbidden access
    return user_type

def generate_token(email, user_type):
    base_token = str(uuid.uuid4())
    if user_type == 'admin':
        return 'adm-' + base_token
    elif user_type == 'user':
        return 'usr-' + base_token
    else:
        return 'oth-' + base_token

def check_permission(user_type, permission):
    return user_permissions.get(user_type, {}).get(permission, False)

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

ns = api.namespace('library', description='Library operations')

book_model = api.model('Book', {
    'title': fields.String(required=True, description='The book title'),
    'author': fields.String(required=True, description='The book author')
})

@ns.route('/generate_token')
class TokenGenerator(Resource):
    token_model = api.model('TokenGeneration', {
        'email': fields.String(required=True, description='User Email'),
        'user_type': fields.String(required=True, description='User Type')
    })

    @ns.expect(token_model)
    def post(self):
        data = request.json
        token = generate_token(data['email'], data['user_type'])
        return {'token': token}

@ns.route('/books')
class BookList(Resource):
    @ns.doc('list_books', security='Bearer Auth')
    def get(self):
        user_type = require_auth()
        books = query_db('SELECT * FROM books')
        return [dict(book) for book in books]

    @ns.expect(book_model)
    @ns.doc('create_book', security='Bearer Auth')
    def post(self):
        user_type = require_auth()
        if not check_permission(user_type, 'write'):
            abort(403, "User does not have write permission")
        db = get_db()
        data = request.json
        db.execute('INSERT INTO books (title, author) VALUES (?, ?)', (data['title'], data['author']))
        db.commit()
        return {'message': 'Book added'}, 201

@ns.route('/book/<int:book_id>')
@ns.param('book_id', 'The book identifier')
class Book(Resource):
    @ns.doc('get_book', security='Bearer Auth')
    def get(self, book_id):
        user_type = require_auth()
        if not check_permission(user_type, 'read'):
            abort(403, "User does not have read permission")
        book = query_db('SELECT * FROM books WHERE id = ?', [book_id], one=True)
        if book is None:
            api.abort(404, "Book {} doesn't exist".format(book_id))
        return dict(book)

    @ns.expect(book_model)
    @ns.doc('update_book', security='Bearer Auth')
    def put(self, book_id):
        user_type = require_auth()
        if not check_permission(user_type, 'write'):
            abort(403, "User does not have write permission")
        db = get_db()
        data = request.json
        db.execute('UPDATE books SET title = ?, author = ? WHERE id = ?', (data['title'], data['author'], book_id))
        db.commit()
        return {'message': 'Book updated'}

    @ns.doc('delete_book', security='Bearer Auth')
    def delete(self, book_id):
        user_type = require_auth()
        if not check_permission(user_type, 'write'):
            abort(403, "User does not have write permission")
        db = get_db()
        db.execute('DELETE FROM books WHERE id = ?', (book_id,))
        db.commit()
        return {'message': 'Book deleted'}

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
