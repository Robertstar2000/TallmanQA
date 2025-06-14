import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, session, url_for, jsonify # Added jsonify
from app import app as flask_app  # Original app
from app.models import User

# It's better to configure the app for testing, e.g., TESTING=True
# Create a new app instance for testing or configure the existing one
# For this example, we'll use flask_app and assume it can be configured or used as is.

class AuthRoutesTests(unittest.TestCase):

    def setUp(self):
        # Configure the app for testing
        flask_app.config['TESTING'] = True
        flask_app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for simpler test forms
        flask_app.config['SECRET_KEY'] = 'test_secret_key' # Needed for session management
        self.app = flask_app
        self.client = self.app.test_client()

        # Mock users for authentication
        self.test_user = User(id="user1", name="Test User", email="test@example.com", status="user", hashed_password="")
        self.test_user.set_password("password123")

        self.admin_user = User(id="admin1", name="Admin User", email="admin@example.com", status="admin", hashed_password="")
        self.admin_user.set_password("adminpass")

        self.mock_users = [self.test_user, self.admin_user]

        # Patch load_users where it's looked up by routes.py
        # This is often app.load_users if it's initialized that way in app/__init__.py
        # or directly app.routes.load_users if imported there.
        # Assuming it's available via the app instance or directly in app.routes
        self.load_users_patch = patch('app.routes.load_users') # Or 'app.load_users'
        self.mock_load_users = self.load_users_patch.start()
        self.mock_load_users.return_value = self.mock_users

        # Also patch load_users if it's directly used in app/__init__.py for flask_app setup
        # if that affects route registration or app context during tests
        self.app_load_users_patch = patch('app.load_users')
        self.mock_app_load_users = self.app_load_users_patch.start()
        self.mock_app_load_users.return_value = self.mock_users


    def tearDown(self):
        self.load_users_patch.stop()
        self.app_load_users_patch.stop()
        # Clear session after each test if necessary
        with self.client.session_transaction() as sess:
            sess.clear()


    def test_login_page_get(self):
        with self.app.app_context(): # Ensure app context for url_for
            response = self.client.get(url_for('login'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data) # Check for common login page text

    def test_login_success(self):
        with self.app.app_context():
            login_url = url_for('login')
            ask_ai_url = url_for('ask_ai_get') # Expected redirect URL

        response = self.client.post(login_url, data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=False) # Do not follow redirects to check session and JSON response

        self.assertEqual(response.status_code, 200) # POST to /login returns JSON
        json_response = response.get_json()
        self.assertEqual(json_response['status'], 'success')
        self.assertEqual(json_response['redirect_url'], ask_ai_url)

        # Check session variables
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('user_id'), self.test_user.id)
            self.assertEqual(sess.get('status'), self.test_user.status)

    def test_login_invalid_credentials(self):
        with self.app.app_context():
            login_url = url_for('login')
        response = self.client.post(login_url, data={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 401) # Unauthorized
        json_response = response.get_json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn('Invalid email or password', json_response['message'])
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('user_id'))

    def test_login_missing_fields(self):
        with self.app.app_context():
            login_url = url_for('login')
        response = self.client.post(login_url, data={'email': 'test@example.com'}) # Missing password
        self.assertEqual(response.status_code, 400) # Bad request
        json_response = response.get_json()
        self.assertEqual(json_response['status'], 'error')
        self.assertIn('Email and password required', json_response['message'])


    def test_logout(self):
        with self.app.app_context():
            login_url = url_for('login')
            logout_url = url_for('logout')

        # First, log in a user
        self.client.post(login_url, data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        # Check session is set
        with self.client.session_transaction() as sess:
            self.assertIsNotNone(sess.get('user_id'))

        # Then, log out
        response = self.client.get(logout_url, follow_redirects=False) # Check redirect to login
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertTrue(response.location.endswith(login_url))

        # Check session is cleared
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('user_id'))
            self.assertIsNone(sess.get('status'))


    def test_login_required_decorator_redirect(self):
        # Access a login-required page without being logged in
        with self.app.app_context():
            ask_url = url_for('ask_ai_get')
            login_url_with_next = url_for('login', next=ask_url)

        response = self.client.get(ask_url, follow_redirects=False)
        self.assertEqual(response.status_code, 302) # Redirect to login
        self.assertTrue(response.location.endswith(login_url_with_next))

    def test_login_required_decorator_ajax_json_response(self):
        with self.app.app_context():
            ask_api_url = url_for('ask_ai_post') # An AJAX-expected endpoint
            login_url = url_for('login')

        response = self.client.post(ask_api_url, json={}, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 401) # Unauthorized
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'error')
        self.assertEqual(json_data['message'], 'Login required')
        self.assertTrue(json_data['redirect_url'].endswith(login_url + f"?next={ask_api_url}"))


    def test_admin_required_decorator_redirect(self):
        # Log in as a non-admin user
        with self.app.app_context():
            login_url = url_for('login')
            manage_users_url = url_for('manage_users')
            index_url = url_for('index') # Admin required redirects to index if permission denied

        self.client.post(login_url, data={
            'email': 'test@example.com', # Non-admin
            'password': 'password123'
        })

        response = self.client.get(manage_users_url, follow_redirects=False)
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertTrue(response.location.endswith(index_url))

    def test_admin_required_decorator_ajax_json_response(self):
        # Log in as non-admin
        with self.app.app_context():
            login_url = url_for('login')
            api_add_user_url = url_for('api_add_user') # An admin API endpoint

        self.client.post(login_url, data={'email': 'test@example.com', 'password': 'password123'})

        response = self.client.post(api_add_user_url, json={}, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 403) # Forbidden
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'error')
        self.assertEqual(json_data['message'], 'Admin access required')


    def test_admin_can_access_admin_page(self):
        # Log in as admin
        with self.app.app_context():
            login_url = url_for('login')
            manage_users_url = url_for('manage_users')

        self.client.post(login_url, data={
            'email': 'admin@example.com',
            'password': 'adminpass'
        })
        response = self.client.get(manage_users_url)
        self.assertEqual(response.status_code, 200) # Admin should access successfully


if __name__ == '__main__':
    unittest.main()
