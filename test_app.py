import unittest
from app import app, init_db
import json

class FlaskLibraryAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        init_db() 
        self.token = self.generate_token()

    def tearDown(self):
        pass  

    def generate_token(self):
        response = self.app.post('/library/generate_token', data=json.dumps({'email': 'test@example.com', 'user_type': 'admin'}), content_type='application/json')
        token_data = json.loads(response.data)
        return token_data['token']

    def test_get_books(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = self.app.get('/library/books', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'book' in response.data)

    def test_generate_token(self):
        response = self.app.post('/library/generate_token', data=json.dumps({'email': 'test@example.com', 'user_type': 'admin'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'token' in response.data)

    def test_add_book(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = self.app.post('/library/books', headers=headers, data=json.dumps({'title': 'New Book', 'author': 'Author'}), content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_update_book(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = self.app.put('/library/book/1', headers=headers, data=json.dumps({'title': 'Updated Book', 'author': 'New Author'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_delete_book(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = self.app.delete('/library/book/1', headers=headers)
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
