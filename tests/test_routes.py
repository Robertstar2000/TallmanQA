import unittest
from app import app
from flask import url_for

class TestRoutes(unittest.TestCase):
    def setUp(self):
        # Set up Flask test client
        self.app = app.test_client()
        self.app.testing = True

    def test_index_redirect(self):
        # Should redirect to login or ask_ai_get
        response = self.app.get('/')
        self.assertIn(response.status_code, [302, 200])

    def test_login_get(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'login', response.data.lower())

    def test_login_post_missing_fields(self):
        response = self.app.post('/login', data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'email and password are required', response.data.lower())

    def test_logout_route(self):
        response = self.app.get('/logout')
        self.assertIn(response.status_code, [302, 200])

    # Add more tests for protected/admin routes as needed

if __name__ == '__main__':
    unittest.main()
