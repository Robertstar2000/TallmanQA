import unittest
from unittest.mock import patch, mock_open, call
import json # Ensure json is imported
from app.utils import (
    load_users,
    save_users,
    get_qa_filepath,
    load_qa_data,
    append_qa_pair,
    USER_FILE,
    TALLMAN_QA_FILE,
    MCR_QA_FILE,
    BRADLEY_QA_FILE
)
from app.models import User, QA

# Define these constants at the module level if utils.py expects them
# However, utils.py already defines them, so direct import is fine.

class TestUserFileOperations(unittest.TestCase):

    @patch('app.utils.open', new_callable=mock_open, read_data='''[
        {"id": "1", "name": "Test User", "email": "test@example.com", "status": "user", "hashed_password": "pw1"},
        {"id": "2", "name": "Admin User", "email": "admin@example.com", "status": "admin", "hashed_password": "pw2"}
    ]''')
    def test_load_users_success(self, mock_file):
        users = load_users()
        self.assertEqual(len(users), 2)
        self.assertIsInstance(users[0], User)
        self.assertEqual(users[0].name, "Test User")
        self.assertEqual(users[1].status, "admin")
        mock_file.assert_called_once_with(USER_FILE, 'r')

    @patch('app.utils.open', new_callable=mock_open, read_data='[]')
    def test_load_users_empty_file(self, mock_file):
        users = load_users()
        self.assertEqual(len(users), 0)
        mock_file.assert_called_once_with(USER_FILE, 'r')

    @patch('app.utils.open', side_effect=FileNotFoundError)
    def test_load_users_file_not_found(self, mock_file):
        users = load_users()
        self.assertEqual(len(users), 0)
        # The open call is still attempted.
        # No need to assert mock_file.assert_called_once_with(USER_FILE, 'r')
        # as the side_effect is what we test.

    @patch('app.utils.open', new_callable=mock_open, read_data='') # Simulate empty file content
    def test_load_users_empty_content_returns_empty_list(self, mock_file):
        users = load_users()
        self.assertEqual(users, [])
        mock_file.assert_called_once_with(USER_FILE, 'r')

    @patch('app.utils.open', new_callable=mock_open)
    def test_save_users(self, mock_file):
        users_to_save = [
            User(id="3", name="Save User 1", email="save1@example.com", status="user", hashed_password="pw3"),
            User(id="4", name="Save User 2", email="save2@example.com", status="admin", hashed_password="pw4")
        ]
        save_users(users_to_save)

        mock_file.assert_called_once_with(USER_FILE, 'w')
        handle = mock_file() # Get the file handle mock

        # Get all write calls
        written_content_calls = handle.write.call_args_list
        # Concatenate all written strings
        written_content = "".join(c[0][0] for c in written_content_calls)

        expected_data = [user.to_dict() for user in users_to_save]
        # The content written to file by json.dump will have newlines and indents
        # json.dumps produces a string representation that matches json.dump to a file
        expected_json_string = json.dumps(expected_data, indent=4)

        self.assertEqual(written_content, expected_json_string)


class TestQAFileOperations(unittest.TestCase):

    def test_get_qa_filepath(self):
        self.assertEqual(get_qa_filepath("Tallman"), TALLMAN_QA_FILE)
        self.assertEqual(get_qa_filepath("MCR"), MCR_QA_FILE)
        self.assertEqual(get_qa_filepath("Bradley"), BRADLEY_QA_FILE)
        with self.assertRaises(ValueError):
            get_qa_filepath("InvalidCompany")

    @patch('app.utils.open', new_callable=mock_open, read_data='''Question 1
Answer 1

Question 2
Answer 2''')
    @patch('uuid.uuid4') # Mock uuid4 to control IDs
    def test_load_qa_data_success(self, mock_uuid, mock_file):
        mock_uuid.return_value.hex = "test_uuid_1" # First call
        def uuid_side_effect(): # Mock subsequent calls if needed, or set different return_value.hex
            # This example assumes each QA item gets a new UUID hex
            # For simplicity, let's make it deterministic
            if mock_uuid.call_count == 1:
                return type('obj', (object,), {'hex' : "test_uuid_1"})
            return type('obj', (object,), {'hex' : "test_uuid_2"})
        mock_uuid.side_effect = uuid_side_effect


        qa_list = load_qa_data("Tallman")
        self.assertEqual(len(qa_list), 2)
        self.assertIsInstance(qa_list[0], QA)
        self.assertEqual(qa_list[0].question, "Question 1")
        self.assertEqual(qa_list[0].answer, "Answer 1")
        self.assertEqual(qa_list[0].company, "Tallman")
        self.assertEqual(qa_list[0].id, "test_uuid_1") # Check mocked ID
        self.assertEqual(qa_list[1].id, "test_uuid_2") # Check mocked ID for second item
        mock_file.assert_called_once_with(TALLMAN_QA_FILE, 'r')


    @patch('app.utils.open', new_callable=mock_open, read_data='''##Update##
Question 1
Answer 1''')
    @patch('uuid.uuid4')
    def test_load_qa_data_with_update_tag(self, mock_uuid, mock_file):
        mock_uuid.return_value.hex = "test_uuid_3"
        qa_list = load_qa_data("MCR")
        self.assertEqual(len(qa_list), 1)
        self.assertEqual(qa_list[0].question, "Question 1")
        self.assertEqual(qa_list[0].id, "test_uuid_3")
        mock_file.assert_called_once_with(MCR_QA_FILE, 'r')

    @patch('app.utils.open', side_effect=FileNotFoundError)
    def test_load_qa_data_file_not_found(self, mock_file):
        qa_list = load_qa_data("Bradley")
        self.assertEqual(len(qa_list), 0)

    # Mocking sentence_transformer_ef and ChromaDB interactions for append_qa_pair
    @patch('app.utils.sentence_transformer_ef', new=None) # Simulate embedding function not available
    @patch('app.utils.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_append_qa_pair_no_chroma(self, mock_uuid, mock_file):
        mock_uuid.return_value.hex = "append_uuid_1"
        company = "Tallman"
        question = "New Q"
        answer = "New A"

        returned_qa = append_qa_pair(company, question, answer, is_update=False)

        mock_file.assert_called_once_with(TALLMAN_QA_FILE, 'a')
        handle = mock_file()
        # Check calls to write to ensure correct format
        # Expected write calls: f"{question}\n", f"{answer}\n", "\n\n"
        self.assertIn(call(f"{question}\n"), handle.write.call_args_list)
        self.assertIn(call(f"{answer}\n"), handle.write.call_args_list)
        self.assertIn(call("\n\n"), handle.write.call_args_list)


        self.assertEqual(returned_qa.id, "append_uuid_1")
        self.assertEqual(returned_qa.question, question)
        self.assertEqual(returned_qa.answer, answer)
        self.assertEqual(returned_qa.company, company)

    @patch('app.utils.sentence_transformer_ef', new=None) # Simulate embedding function not available
    @patch('app.utils.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    def test_append_qa_pair_with_update_tag_no_chroma(self, mock_uuid, mock_file):
        mock_uuid.return_value.hex = "append_uuid_2"
        company = "MCR"
        question = "Updated Q"
        answer = "Updated A"

        append_qa_pair(company, question, answer, is_update=True)

        mock_file.assert_called_once_with(MCR_QA_FILE, 'a')
        handle = mock_file()
        # Check that call("##Update##\n") is the first thing written.
        # This requires careful checking of call order if other writes happen before it in a real scenario.
        # For an append, it's simpler.
        expected_calls = [
            call("##Update##\n"),
            call(f"{question}\n"),
            call(f"{answer}\n"),
            call("\n\n")
        ]
        handle.write.assert_has_calls(expected_calls, any_order=False)

    # Test with ChromaDB mocked (basic case)
    @patch('app.utils.get_or_create_collection')
    @patch('app.utils.add_qa_to_collection')
    @patch('app.utils.open', new_callable=mock_open)
    @patch('uuid.uuid4')
    @patch('app.utils.sentence_transformer_ef') # Ensure it's not None
    def test_append_qa_pair_with_chroma(self, mock_ef, mock_uuid, mock_file_open, mock_add_qa, mock_get_collection):
        # Ensure sentence_transformer_ef is not None for this test
        # The patch decorator already does this by replacing it with a MagicMock
        # if 'new' is not specified or if it's a MagicMock instance.
        # Or, explicitly set it:
        # app.utils.sentence_transformer_ef = MagicMock()

        mock_uuid.return_value.hex = "append_uuid_3"
        mock_collection_instance = unittest.mock.MagicMock()
        mock_get_collection.return_value = mock_collection_instance

        company = "Bradley"
        question = "Chroma Q"
        answer = "Chroma A"

        returned_qa = append_qa_pair(company, question, answer)

        mock_file_open.assert_called_once_with(BRADLEY_QA_FILE, 'a')
        mock_get_collection.assert_called_once_with(company)
        mock_add_qa.assert_called_once()

        # Check that the QA object passed to add_qa_to_collection is correct
        args, _ = mock_add_qa.call_args
        self.assertEqual(args[0], mock_collection_instance) # collection object
        passed_qa_item = args[1] # QA object
        self.assertEqual(passed_qa_item.id, "append_uuid_3")
        self.assertEqual(passed_qa_item.question, question)


if __name__ == '__main__':
    unittest.main()
