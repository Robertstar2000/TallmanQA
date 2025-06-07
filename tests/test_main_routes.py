import unittest
from unittest.mock import patch, MagicMock, ANY
from flask import Flask, session, url_for, jsonify # Added jsonify
from app import app as flask_app # Original app
from app.models import User, QA

# Utility to log in a user
def login_user(client, email, password):
    with flask_app.app_context():
        return client.post(url_for('login'), data={'email': email, 'password': password})

class MainRoutesTests(unittest.TestCase):

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
        self.mock_users = [self.test_user, self.admin_user]

        # Patch load_users
        self.load_users_patch = patch('app.routes.load_users', return_value=self.mock_users)
        self.mock_load_users = self.load_users_patch.start()

        self.app_load_users_patch = patch('app.load_users', return_value=self.mock_users)
        self.mock_app_load_users = self.app_load_users_patch.start()

        # Mock utilities used in routes
        self.get_or_create_collection_patch = patch('app.routes.get_or_create_collection')
        self.mock_get_or_create_collection = self.get_or_create_collection_patch.start()
        self.mock_collection_instance = MagicMock()
        self.mock_get_or_create_collection.return_value = self.mock_collection_instance

        self.query_collection_patch = patch('app.routes.query_collection')
        self.mock_query_collection = self.query_collection_patch.start()

        self.get_llm_answer_patch = patch('app.routes.get_llm_answer')
        self.mock_get_llm_answer = self.get_llm_answer_patch.start()

        self.format_snippets_for_llm_patch = patch('app.routes.format_snippets_for_llm')
        self.mock_format_snippets_for_llm = self.format_snippets_for_llm_patch.start()

        self.get_corrected_llm_answer_patch = patch('app.routes.get_corrected_llm_answer')
        self.mock_get_corrected_llm_answer = self.get_corrected_llm_answer_patch.start()

        self.append_qa_pair_patch = patch('app.routes.append_qa_pair')
        self.mock_append_qa_pair = self.append_qa_pair_patch.start()


    def tearDown(self):
        self.load_users_patch.stop()
        self.app_load_users_patch.stop()
        self.get_or_create_collection_patch.stop()
        self.query_collection_patch.stop()
        self.get_llm_answer_patch.stop()
        self.format_snippets_for_llm_patch.stop()
        self.get_corrected_llm_answer_patch.stop()
        self.append_qa_pair_patch.stop()
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_ask_ai_get_page_authenticated(self):
        login_user(self.client, 'test@example.com', 'password123')
        with self.app.app_context():
            response = self.client.get(url_for('ask_ai_get'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Ask AI', response.data) # Check for a title or specific text

    def test_ask_ai_post_api_success(self):
        login_user(self.client, 'test@example.com', 'password123')

        self.mock_query_collection.return_value = [{'id': 'doc1', 'question': 'Q1', 'answer': 'A1'}]
        self.mock_get_llm_answer.return_value = "LLM Answer"
        self.mock_format_snippets_for_llm.return_value = "Formatted Snippets"

        payload = {
            'user_question': 'Test question?',
            'company': 'Tallman',
            'question_type': 'Product'
        }
        with self.app.app_context():
            response = self.client.post(url_for('ask_ai_post'), json=payload)

        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'success')
        self.assertEqual(json_data['answer'], 'LLM Answer')
        self.assertEqual(json_data['retrieved_snippets_formatted'], 'Formatted Snippets')

        self.mock_get_or_create_collection.assert_called_once_with('Tallman')
        self.mock_query_collection.assert_called_once_with(self.mock_collection_instance, 'Test question?', n_results=3)
        self.mock_get_llm_answer.assert_called_once_with('Test question?', 'Tallman', 'Product', [{'id': 'doc1', 'question': 'Q1', 'answer': 'A1'}])

    def test_ask_ai_post_api_missing_fields(self):
        login_user(self.client, 'test@example.com', 'password123')
        payload = {'user_question': 'Test question?'} # Missing company and type
        with self.app.app_context():
            response = self.client.post(url_for('ask_ai_post'), json=payload)
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'error')
        self.assertIn('Missing required fields', json_data['message'])

    def test_ask_ai_post_api_invalid_company_or_type(self):
        login_user(self.client, 'test@example.com', 'password123')
        payload = {'user_question': 'Q', 'company': 'InvalidCo', 'question_type': 'Product'}
        with self.app.app_context():
            response = self.client.post(url_for('ask_ai_post'), json=payload)
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertIn('Invalid company', json_data['message'])

        payload = {'user_question': 'Q', 'company': 'Tallman', 'question_type': 'InvalidType'}
        with self.app.app_context():
            response = self.client.post(url_for('ask_ai_post'), json=payload)
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertIn('Invalid question type', json_data['message'])


    def test_ask_ai_post_api_llm_error(self):
        login_user(self.client, 'test@example.com', 'password123')
        self.mock_query_collection.return_value = []
        self.mock_get_llm_answer.return_value = "Error generating answer from LLM" # Simulate error

        payload = {'user_question': 'Q', 'company': 'Tallman', 'question_type': 'Product'}
        with self.app.app_context():
            response = self.client.post(url_for('ask_ai_post'), json=payload)

        self.assertEqual(response.status_code, 500)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'error')
        self.assertEqual(json_data['message'], 'Error generating answer from LLM')

    def test_correct_answer_page_get_admin(self):
        login_user(self.client, 'admin@example.com', 'adminpass') # Login as admin
        with self.app.app_context():
            response = self.client.get(url_for('correct_answer_page_get',
                                               original_question="OQ", incorrect_answer="IA", company="Tallman"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Correct Answer', response.data)
        self.assertIn(b'OQ', response.data) # Check if params are passed to template

    def test_correct_answer_post_api_success_admin(self):
        login_user(self.client, 'admin@example.com', 'adminpass')

        self.mock_get_corrected_llm_answer.return_value = "Corrected LLM Answer"
        mock_qa_item = MagicMock(spec=QA)
        mock_qa_item.id = "new_qa_id"
        self.mock_append_qa_pair.return_value = mock_qa_item

        payload = {
            'original_question': 'OQ',
            'incorrect_answer': 'IA',
            'user_correction_text': 'Correction',
            'company': 'Tallman'
        }
        with self.app.app_context():
            response = self.client.post(url_for('correct_answer_post'), json=payload)

        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'success')
        self.assertEqual(json_data['new_answer'], 'Corrected LLM Answer')
        self.assertEqual(json_data['qa_id'], 'new_qa_id')

        self.mock_get_corrected_llm_answer.assert_called_once_with('OQ', 'IA', 'Correction', 'Tallman')
        self.mock_append_qa_pair.assert_called_once_with('Tallman', 'OQ', 'Corrected LLM Answer', is_update=True)

    def test_correct_answer_post_api_missing_fields_admin(self):
        login_user(self.client, 'admin@example.com', 'adminpass')
        payload = {'original_question': 'OQ'} # Missing other fields
        with self.app.app_context():
            response = self.client.post(url_for('correct_answer_post'), json=payload)
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'error')
        self.assertIn('Missing required fields', json_data['message'])

    def test_correct_answer_post_api_llm_correction_error_admin(self):
        login_user(self.client, 'admin@example.com', 'adminpass')
        self.mock_get_corrected_llm_answer.return_value = "Error generating corrected answer from LLM"
        payload = {'original_question': 'OQ', 'incorrect_answer': 'IA', 'user_correction_text': 'UC', 'company': 'Tallman'}
        with self.app.app_context():
            response = self.client.post(url_for('correct_answer_post'), json=payload)
        self.assertEqual(response.status_code, 500)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'error')
        self.assertEqual(json_data['message'], 'Error generating corrected answer from LLM')

    def test_correct_answer_post_api_non_admin(self):
        login_user(self.client, 'test@example.com', 'password123') # Login as non-admin
        payload = {'original_question': 'OQ', 'incorrect_answer': 'IA', 'user_correction_text': 'UC', 'company': 'Tallman'}
        with self.app.app_context():
            response = self.client.post(url_for('correct_answer_post'), json=payload, headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 403) # Forbidden
        json_data = response.get_json()
        self.assertEqual(json_data['message'], 'Admin access required')


if __name__ == '__main__':
    unittest.main()
