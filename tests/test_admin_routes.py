import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, session, url_for
from app import app as flask_app # Original app
from app.models import User

# Utility to log in a user
def login_user(client, email, password):
    with flask_app.app_context():
        return client.post(url_for('login'), data={'email': email, 'password': password})

class AdminRoutesTests(unittest.TestCase):

    def setUp(self):
        flask_app.config['TESTING'] = True
        flask_app.config['WTF_CSRF_ENABLED'] = False
        flask_app.config['SECRET_KEY'] = 'test_secret_key'
        self.app = flask_app
        self.client = self.app.test_client()

        # Mock users
        self.test_user = User(id="user1", name="Test User", email="test@example.com", status="user", hashed_password="")
        self.test_user.set_password("password123")
        self.admin_user = User(id="admin1", name="Admin User", email="admin@example.com", status="admin", hashed_password="")
        self.admin_user.set_password("adminpass")

        # Ensure users have to_dict method that matches what's expected by the template
        # self.admin_user_dict = {'id': 'admin1', 'name': 'Admin User', 'email': 'admin@example.com', 'status': 'admin'}
        # self.test_user_dict = {'id': 'user1', 'name': 'Test User', 'email': 'test@example.com', 'status': 'user'}


        self.mock_users_list = [self.test_user, self.admin_user]
        # self.mock_users_dicts = [self.test_user.to_dict(), self.admin_user.to_dict()]


        # Patch load_users where it's looked up by routes.py or app
        self.load_users_patch = patch('app.routes.load_users')
        self.mock_load_users = self.load_users_patch.start()
        self.mock_load_users.return_value = self.mock_users_list

        self.app_load_users_patch = patch('app.load_users') # If app object itself uses it
        self.mock_app_load_users = self.app_load_users_patch.start()
        self.mock_app_load_users.return_value = self.mock_users_list


    def tearDown(self):
        self.load_users_patch.stop()
        self.app_load_users_patch.stop()
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_manage_users_page_get_admin(self):
        login_user(self.client, 'admin@example.com', 'adminpass') # Login as admin
        with self.app.app_context():
            response = self.client.get(url_for('manage_users'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Manage Users', response.data)
        # Check if user data is present (mocked users)
        self.assertIn(b'Admin User', response.data)
        self.assertIn(b'test@example.com', response.data)
        self.mock_load_users.assert_called_once()


    def test_manage_users_page_get_non_admin(self):
        login_user(self.client, 'test@example.com', 'password123') # Login as non-admin
        with self.app.app_context():
            response = self.client.get(url_for('manage_users'), follow_redirects=False)
        self.assertEqual(response.status_code, 302) # Should redirect
        with self.app.app_context():
            self.assertTrue(response.location.endswith(url_for('index')))

    def test_api_add_user_placeholder_admin(self):
        login_user(self.client, 'admin@example.com', 'adminpass')
        with self.app.app_context():
            response = self.client.post(url_for('api_add_user'), json={})
        self.assertEqual(response.status_code, 501) # Not Implemented
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'not_implemented')

    def test_api_manage_user_put_placeholder_admin(self):
        login_user(self.client, 'admin@example.com', 'adminpass')
        with self.app.app_context():
            response = self.client.put(url_for('api_manage_user', user_id='user1'), json={})
        self.assertEqual(response.status_code, 501)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'not_implemented')
        self.assertIn('Edit user user1 not yet implemented', json_data['message'])

    def test_api_manage_user_delete_placeholder_admin(self):
        login_user(self.client, 'admin@example.com', 'adminpass')
        with self.app.app_context():
            response = self.client.delete(url_for('api_manage_user', user_id='user1'))
        self.assertEqual(response.status_code, 501)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'not_implemented')
        self.assertIn('Delete user user1 not yet implemented', json_data['message'])

    def test_api_admin_routes_non_admin(self):
        login_user(self.client, 'test@example.com', 'password123') # Login as non-admin
        with self.app.app_context():
            add_user_url = url_for('api_add_user')
            manage_user_url_put = url_for('api_manage_user', user_id='user1')
            manage_user_url_delete = url_for('api_manage_user', user_id='user1')

        common_headers = {'X-Requested-With': 'XMLHttpRequest'} # Simulate AJAX for JSON error

        response_add = self.client.post(add_user_url, json={}, headers=common_headers)
        self.assertEqual(response_add.status_code, 403)
        self.assertEqual(response_add.get_json()['message'], 'Admin access required')

        response_put = self.client.put(manage_user_url_put, json={}, headers=common_headers)
        self.assertEqual(response_put.status_code, 403)
        self.assertEqual(response_put.get_json()['message'], 'Admin access required')

        response_delete = self.client.delete(manage_user_url_delete, headers=common_headers)
        self.assertEqual(response_delete.status_code, 403)
        self.assertEqual(response_delete.get_json()['message'], 'Admin access required')


if __name__ == '__main__':
    unittest.main()
