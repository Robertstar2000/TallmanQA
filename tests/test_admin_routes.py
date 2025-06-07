import unittest
import json # Added for request bodies
import io # Added for file uploads
from unittest.mock import patch, MagicMock, call # Added call for checking multiple calls
from flask import Flask, session, url_for
from app import app as flask_app # Original app
from app.models import User, QA # Added QA model

# Utility to log in a user
def login_admin(client, mock_load_users_func, admin_user_obj, admin_password):
    """Helper to log in the admin user, using the provided mock for load_users."""
    mock_load_users_func.return_value = [admin_user_obj] # Ensure only admin user is findable during login
    with flask_app.app_context():
        response = client.post(url_for('login'), data=json.dumps({
            'email': admin_user_obj.email,
            'password': admin_password
        }), content_type='application/json')
    assert response.status_code == 200 # Assuming login success is 200
    # After login, restore the main mock_users_list for other operations if needed,
    # or set it specifically for each test. For simplicity, we'll often reset it in tests.
    # mock_load_users_func.return_value = self.mock_users_list # Or whatever the test needs next


class AdminRoutesTests(unittest.TestCase):

    def setUp(self):
        flask_app.config['TESTING'] = True
        flask_app.config['WTF_CSRF_ENABLED'] = False
        flask_app.config['SECRET_KEY'] = 'test_secret_key'
        self.app = flask_app
        self.client = self.app.test_client()
        self.app_context = self.app.app_context() # Create an app context
        self.app_context.push() # Push it to use url_for

        # Mock users
        self.admin_password = "adminpass"
        self.user_password = "password123"
        self.admin_user = User(id="admin1", name="Admin User", email="admin@example.com", status="admin")
        self.admin_user.set_password(self.admin_password)
        self.test_user = User(id="user1", name="Test User", email="test@example.com", status="user")
        self.test_user.set_password(self.user_password)

        self.mock_users_list = [self.admin_user, self.test_user]

        # Patchers
        self.patchers = {
            'load_users': patch('app.routes.load_users'),
            'save_users': patch('app.routes.save_users'),
            'uuid4': patch('app.routes.uuid.uuid4'),
            'load_qa_data': patch('app.routes.load_qa_data'),
            'append_qa_pair': patch('app.routes.append_qa_pair'),
            # Also patch load_users used by app.login route if it's different
            'app_load_users': patch('app.load_users', MagicMock(return_value=self.mock_users_list))
        }
        self.mocks = {name: p.start() for name, p in self.patchers.items()}

        self.mocks['load_users'].return_value = self.mock_users_list
        self.mocks['app_load_users'].return_value = self.mock_users_list # For login route
        self.mocks['uuid4'].return_value = MagicMock(hex='new_user_uuid_123')


    def tearDown(self):
        for p in self.patchers.values():
            p.stop()
        with self.client.session_transaction() as sess: # Clear session
            sess.clear()
        self.app_context.pop() # Pop app context

    def _login_admin(self):
        # Use the main mock_load_users for login, ensuring admin_user is in its return_value
        self.mocks['load_users'].return_value = [self.admin_user]
        self.mocks['app_load_users'].return_value = [self.admin_user] # Ensure login route also sees admin
        response = self.client.post(url_for('login'), data=json.dumps({
            'email': self.admin_user.email,
            'password': self.admin_password
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200, f"Admin login failed: {response.get_json()}")
        # Restore mock_users_list for subsequent operations in the test if needed
        self.mocks['load_users'].return_value = self.mock_users_list
        self.mocks['app_load_users'].return_value = self.mock_users_list


    def test_manage_users_page_get_admin(self):
        self._login_admin()
        response = self.client.get(url_for('manage_users'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Panel', response.data) # Updated link text
        self.assertIn(b'Admin User', response.data)
        self.assertIn(b'test@example.com', response.data)
        self.mocks['load_users'].assert_called() # Called at least once by manage_users or login

    def test_manage_users_page_get_non_admin(self):
        # Login as non-admin (test_user)
        self.mocks['load_users'].return_value = [self.test_user]
        self.mocks['app_load_users'].return_value = [self.test_user]
        response = self.client.post(url_for('login'), data=json.dumps({
            'email': self.test_user.email,
            'password': self.user_password
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        self.mocks['load_users'].return_value = self.mock_users_list # Reset for the next call
        response = self.client.get(url_for('manage_users'), follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith(url_for('index')))

    # --- User CRUD API Tests ---
    def test_api_add_user_success(self):
        self._login_admin()
        new_user_data = {
            "name": "New User",
            "email": "new@example.com",
            "password": "newpassword123",
            "status": "user"
        }
        # Ensure load_users returns a list that doesn't contain new@example.com yet
        self.mocks['load_users'].return_value = [self.admin_user, self.test_user]

        response = self.client.post(url_for('api_add_user'), json=new_user_data)

        self.assertEqual(response.status_code, 201)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'success')
        self.assertEqual(json_data['user']['email'], 'new@example.com')
        self.assertEqual(json_data['user']['id'], 'new_user_uuid_123')
        self.assertNotIn('password_hash', json_data['user'])

        # Check that save_users was called with the new user added
        self.mocks['save_users'].assert_called_once()
        saved_users_arg = self.mocks['save_users'].call_args[0][0]
        self.assertEqual(len(saved_users_arg), 3) # admin, test_user, new_user
        newly_added_user = next(u for u in saved_users_arg if u.email == 'new@example.com')
        self.assertIsNotNone(newly_added_user)
        self.assertEqual(newly_added_user.name, "New User")

    def test_api_add_user_duplicate_email(self):
        self._login_admin()
        # self.test_user (email: test@example.com) is already in self.mock_users_list
        self.mocks['load_users'].return_value = self.mock_users_list
        user_data = {
            "name": "Another User",
            "email": self.test_user.email, # Duplicate email
            "password": "password123",
            "status": "user"
        }
        response = self.client.post(url_for('api_add_user'), json=user_data)
        self.assertEqual(response.status_code, 409)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'error')
        self.assertEqual(json_data['message'], 'User with this email already exists')
        self.mocks['save_users'].assert_not_called()

    def test_api_add_user_missing_fields(self):
        self._login_admin()
        response = self.client.post(url_for('api_add_user'), json={"name": "Just Name"})
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'error')
        self.assertEqual(json_data['message'], 'Missing required fields: name, email, password')

    def test_api_add_user_invalid_status(self):
        self._login_admin()
        user_data = {"name": "Bad Status User", "email": "bs@example.com", "password": "pw", "status": "superadmin"}
        response = self.client.post(url_for('api_add_user'), json=user_data)
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertEqual(json_data['message'], "Invalid status. Must be 'user' or 'admin'.")

    def test_api_edit_user_success(self):
        self._login_admin()
        user_to_edit_id = self.test_user.id # user1
        updated_data = {
            "name": "Updated Test User",
            "email": "updated_test@example.com",
            "status": "admin",
            "password": "newpassword456"
        }
        # Ensure user_to_edit_id exists and no conflict with new email
        self.mocks['load_users'].return_value = [self.admin_user, self.test_user]

        response = self.client.put(url_for('api_manage_user', user_id=user_to_edit_id), json=updated_data)
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'success')
        self.assertEqual(json_data['user']['name'], "Updated Test User")
        self.assertEqual(json_data['user']['email'], "updated_test@example.com")
        self.assertEqual(json_data['user']['status'], "admin")

        self.mocks['save_users'].assert_called_once()
        saved_users_arg = self.mocks['save_users'].call_args[0][0]
        edited_user = next(u for u in saved_users_arg if u.id == user_to_edit_id)
        self.assertEqual(edited_user.name, "Updated Test User")
        self.assertTrue(edited_user.check_password("newpassword456")) # Verify password change

    def test_api_edit_user_not_found(self):
        self._login_admin()
        response = self.client.put(url_for('api_manage_user', user_id="nonexistentuser"), json={"name": "test"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()['message'], 'User not found')
        self.mocks['save_users'].assert_not_called()

    def test_api_edit_user_duplicate_email(self):
        self._login_admin()
        # admin_user.email is admin@example.com, test_user.email is test@example.com
        self.mocks['load_users'].return_value = self.mock_users_list
        updated_data = {"email": self.admin_user.email} # Try to change test_user's email to admin_user's email

        response = self.client.put(url_for('api_manage_user', user_id=self.test_user.id), json=updated_data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['message'], 'Email already in use by another user')
        self.mocks['save_users'].assert_not_called()

    def test_api_edit_user_invalid_status(self):
        self._login_admin()
        self.mocks['load_users'].return_value = self.mock_users_list
        updated_data = {"status": "superduperadmin"}
        response = self.client.put(url_for('api_manage_user', user_id=self.test_user.id), json=updated_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], "Invalid status. Must be 'user' or 'admin'.")

    def test_api_delete_user_success(self):
        self._login_admin()
        user_to_delete_id = self.test_user.id
        # Ensure user_to_delete_id exists
        self.mocks['load_users'].return_value = [self.admin_user, self.test_user]

        response = self.client.delete(url_for('api_manage_user', user_id=user_to_delete_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['message'], 'User deleted successfully')

        self.mocks['save_users'].assert_called_once()
        saved_users_arg = self.mocks['save_users'].call_args[0][0]
        self.assertEqual(len(saved_users_arg), 1) # Only admin_user should remain
        self.assertTrue(all(u.id != user_to_delete_id for u in saved_users_arg))

    def test_api_delete_user_not_found(self):
        self._login_admin()
        self.mocks['load_users'].return_value = self.mock_users_list
        response = self.client.delete(url_for('api_manage_user', user_id="nonexistentuser"))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()['message'], 'User not found')
        self.mocks['save_users'].assert_not_called()

    # --- Q&A Download API Tests ---
    def test_api_download_qa_success_with_data(self):
        self._login_admin()
        company_name = "Tallman"
        mock_qa_list = [
            QA(id="qa1", question="Q1", answer="A1", company=company_name),
            QA(id="qa2", question="Q2", answer="A2", company=company_name)
        ]
        self.mocks['load_qa_data'].return_value = mock_qa_list

        response = self.client.get(url_for('download_qa_file', company_name=company_name))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertTrue(f"attachment; filename={company_name}_qa_data.json" in response.headers['Content-Disposition'])

        json_data = response.get_json()
        self.assertEqual(len(json_data), 2)
        self.assertEqual(json_data[0]['question'], "Q1")
        self.assertEqual(json_data[1]['id'], "qa2")
        self.mocks['load_qa_data'].assert_called_once_with(company_name)

    def test_api_download_qa_success_no_data(self):
        self._login_admin()
        company_name = "MCR"
        self.mocks['load_qa_data'].return_value = [] # No data

        response = self.client.get(url_for('download_qa_file', company_name=company_name))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertTrue(f"attachment; filename={company_name}_qa_data.json" in response.headers['Content-Disposition'])
        self.assertEqual(response.get_json(), [])
        self.mocks['load_qa_data'].assert_called_once_with(company_name)

    def test_api_download_qa_invalid_company(self):
        self._login_admin()
        response = self.client.get(url_for('download_qa_file', company_name="InvalidCompany"))
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'error')
        self.assertEqual(json_data['message'], 'Invalid or unsupported company name')
        self.mocks['load_qa_data'].assert_not_called()

    # --- Q&A Upload API Tests ---
    def test_api_upload_qa_success(self):
        self._login_admin()
        company_name = "Tallman"
        valid_qa_data = [
            {"question": "Q1 up", "answer": "A1 up"},
            {"question": "Q2 up", "answer": "A2 up"}
        ]
        file_content = json.dumps(valid_qa_data).encode('utf-8')
        mock_file = (io.BytesIO(file_content), 'test_qa.json')

        response = self.client.post(
            url_for('upload_qa_file', company_name=company_name),
            data={'file': mock_file},
            content_type='multipart/form-data'
        )

        self.assertEqual(response.status_code, 201)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'success')
        self.assertEqual(json_data['processed_count'], 2)
        self.assertEqual(json_data['error_count'], 0)

        self.mocks['append_qa_pair'].assert_has_calls([
            call(company_name, "Q1 up", "A1 up"),
            call(company_name, "Q2 up", "A2 up")
        ], any_order=False) # Order should be preserved

    def test_api_upload_qa_invalid_company(self):
        self._login_admin()
        file_content = json.dumps([{"question": "Q", "answer": "A"}]).encode('utf-8')
        mock_file = (io.BytesIO(file_content), 'test.json')
        response = self.client.post(
            url_for('upload_qa_file', company_name="FakeCompany"),
            data={'file': mock_file}, content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], 'Invalid or unsupported company name')
        self.mocks['append_qa_pair'].assert_not_called()

    def test_api_upload_qa_no_file(self):
        self._login_admin()
        response = self.client.post(
            url_for('upload_qa_file', company_name="Tallman"),
            content_type='multipart/form-data' # No file in data
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], 'No file part in the request')

    def test_api_upload_qa_invalid_file_type(self):
        self._login_admin()
        mock_file = (io.BytesIO(b"some text data"), 'test.txt') # Not a .json
        response = self.client.post(
            url_for('upload_qa_file', company_name="Tallman"),
            data={'file': mock_file}, content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], 'Invalid file type. Only .json files are allowed.')

    def test_api_upload_qa_malformed_json(self):
        self._login_admin()
        mock_file = (io.BytesIO(b"[{'question': 'Q1', 'answer': 'A1'"), 'test.json') # Malformed
        response = self.client.post(
            url_for('upload_qa_file', company_name="Tallman"),
            data={'file': mock_file}, content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], 'Invalid JSON format in the uploaded file.')

    def test_api_upload_qa_not_a_list(self):
        self._login_admin()
        file_content = json.dumps({"question": "Q", "answer": "A"}).encode('utf-8') # Dict, not list
        mock_file = (io.BytesIO(file_content), 'test.json')
        response = self.client.post(
            url_for('upload_qa_file', company_name="Tallman"),
            data={'file': mock_file}, content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], 'Invalid JSON content. Expected a list of Q&A objects.')

    def test_api_upload_qa_partial_success_invalid_items(self):
        self._login_admin()
        company_name = "MCR"
        mixed_qa_data = [
            {"question": "Valid Q1", "answer": "Valid A1"},
            {"question_typo": "Missing answer field"}, # Invalid item
            {"answer": "Missing question field"},      # Invalid item
            {"question": "Valid Q2", "answer": "Valid A2"},
            {"question": "Q3", "answer": 123}, # Invalid answer type
            {"question": "", "answer": "Empty question"} # Invalid empty question
        ]
        file_content = json.dumps(mixed_qa_data).encode('utf-8')
        mock_file = (io.BytesIO(file_content), 'test_mixed.json')

        response = self.client.post(
            url_for('upload_qa_file', company_name=company_name),
            data={'file': mock_file}, content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 207) # Multi-Status for partial success
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'partial_success')
        self.assertEqual(json_data['processed_count'], 2) # Only two are valid
        self.assertEqual(json_data['error_count'], 4)
        self.assertEqual(len(json_data['errors']), 4)
        # Check that append_qa_pair was called for valid items only
        self.mocks['append_qa_pair'].assert_has_calls([
            call(company_name, "Valid Q1", "Valid A1"),
            call(company_name, "Valid Q2", "Valid A2")
        ], any_order=False)
        self.assertEqual(self.mocks['append_qa_pair'].call_count, 2)

    def test_api_upload_qa_all_items_fail(self):
        self._login_admin()
        company_name = "Bradley"
        invalid_qa_data = [
            {"question_typo": "Q1", "answer_typo": "A1"},
            {"text": "Some text", "value": "another"}
        ]
        file_content = json.dumps(invalid_qa_data).encode('utf-8')
        mock_file = (io.BytesIO(file_content), 'test_all_invalid.json')

        response = self.client.post(
            url_for('upload_qa_file', company_name=company_name),
            data={'file': mock_file}, content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400) # All failed
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'error')
        self.assertEqual(json_data['processed_count'], 0)
        self.assertEqual(json_data['error_count'], 2)
        self.mocks['append_qa_pair'].assert_not_called()

    def test_api_upload_qa_empty_json_array(self):
        self._login_admin()
        company_name = "Tallman"
        empty_qa_data = []
        file_content = json.dumps(empty_qa_data).encode('utf-8')
        mock_file = (io.BytesIO(file_content), 'test_empty.json')

        response = self.client.post(
            url_for('upload_qa_file', company_name=company_name),
            data={'file': mock_file},
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 200) # OK, but nothing processed
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'success') # Or some other status indicating nothing to do
        self.assertEqual(json_data['processed_count'], 0)
        self.assertEqual(json_data['error_count'], 0)
        self.assertIn(f'No Q&A pairs found in the uploaded file to process for {company_name}', json_data['message'])
        self.mocks['append_qa_pair'].assert_not_called()


    def test_api_admin_routes_non_admin_access(self):
        # Login as non-admin
        self.mocks['load_users'].return_value = [self.test_user]
        self.mocks['app_load_users'].return_value = [self.test_user]
        login_response = self.client.post(url_for('login'), data=json.dumps({
             'email': self.test_user.email, 'password': self.user_password
        }), content_type='application/json')
        self.assertEqual(login_response.status_code, 200)

        common_headers = {'X-Requested-With': 'XMLHttpRequest'}
        admin_routes_params = [
            ('api_add_user', 'POST', {}),
            ('api_manage_user', 'PUT', {'user_id': 'user1'}, {}),
            ('api_manage_user', 'DELETE', {'user_id': 'user1'}, None),
            ('download_qa_file', 'GET', {'company_name': 'Tallman'}, None),
            ('upload_qa_file', 'POST', {'company_name': 'Tallman'}, None), # data for POST with file is different
        ]

        for route_name, method, params, json_data in admin_routes_params:
            with self.subTest(route=route_name, method=method):
                url = url_for(route_name, **params)
                if method == 'POST':
                    if route_name == 'upload_qa_file': # File upload needs different handling
                         # For now, just check endpoint protection without actual file data
                        res = self.client.post(url, headers=common_headers, data={'file': (io.BytesIO(b"test"), 'test.json')})
                    else:
                        res = self.client.post(url, json=json_data, headers=common_headers)
                elif method == 'PUT':
                    res = self.client.put(url, json=json_data, headers=common_headers)
                elif method == 'DELETE':
                    res = self.client.delete(url, headers=common_headers)
                else: # GET
                    res = self.client.get(url, headers=common_headers)

                self.assertEqual(res.status_code, 403, f"Route {route_name} did not return 403 for non-admin.")
                if res.content_type == 'application/json': # API routes should return JSON error
                    self.assertEqual(res.get_json()['message'], 'Admin access required', f"Route {route_name} JSON error message incorrect.")
                else: # Non-API routes might redirect or show HTML error
                    # For this project, admin routes are APIs or redirect.
                    # If it redirects, check the redirect location if necessary.
                    # If it's an HTML page, check for a message.
                    # Current admin_required returns JSON error for AJAX, redirects otherwise.
                    # Since we use common_headers, we expect JSON.
                    pass


    # Remove old placeholder tests
    # Removed old placeholder tests that were here.
    # The test_api_admin_routes_non_admin_access covers generic non-admin access denial.

if __name__ == '__main__':
    unittest.main()
