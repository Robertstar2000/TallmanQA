import unittest
from app.models import User, QA
from werkzeug.security import check_password_hash

class TestUserModel(unittest.TestCase):

    def test_user_creation(self):
        user = User(id="1", name="Test User", email="test@example.com", status="user", hashed_password="password123")
        self.assertEqual(user.id, "1")
        self.assertEqual(user.name, "Test User")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.status, "user")
        self.assertEqual(user.hashed_password, "password123")

    def test_set_password(self):
        user = User(id="2", name="Test User 2", email="test2@example.com", status="admin", hashed_password="")
        user.set_password("newpassword")
        self.assertTrue(user.hashed_password)
        self.assertTrue(check_password_hash(user.hashed_password, "newpassword"))
        self.assertFalse(check_password_hash(user.hashed_password, "wrongpassword"))

    def test_check_password(self):
        user = User(id="3", name="Test User 3", email="test3@example.com", status="user", hashed_password="")
        user.set_password("securepassword")
        self.assertTrue(user.check_password("securepassword"))
        self.assertFalse(user.check_password("incorrectpassword"))

    def test_user_to_dict(self):
        user = User(id="4", name="Dict User", email="dict@example.com", status="admin", hashed_password="hashed_pw_dict")
        user_dict = user.to_dict()
        expected_dict = {
            'id': "4",
            'name': "Dict User",
            'email': "dict@example.com",
            'status': "admin",
            'hashed_password': "hashed_pw_dict"
        }
        self.assertEqual(user_dict, expected_dict)

    def test_user_from_dict(self):
        user_data = {
            'id': "5",
            'name': "From Dict User",
            'email': "fromdict@example.com",
            'status': "user",
            'hashed_password': "hashed_pw_from_dict"
        }
        user = User.from_dict(user_data)
        self.assertEqual(user.id, "5")
        self.assertEqual(user.name, "From Dict User")
        self.assertEqual(user.email, "fromdict@example.com")
        self.assertEqual(user.status, "user")
        self.assertEqual(user.hashed_password, "hashed_pw_from_dict")

class TestQAModel(unittest.TestCase):

    def test_qa_creation(self):
        qa = QA(id="qa1", question="What is Flask?", answer="A web framework.", company="Tech")
        self.assertEqual(qa.id, "qa1")
        self.assertEqual(qa.question, "What is Flask?")
        self.assertEqual(qa.answer, "A web framework.")
        self.assertEqual(qa.company, "Tech")

    def test_qa_to_dict(self):
        qa = QA(id="qa2", question="What is Python?", answer="A programming language.", company="Software")
        qa_dict = qa.to_dict()
        expected_dict = {
            'id': "qa2",
            'question': "What is Python?",
            'answer': "A programming language.",
            'company': "Software"
        }
        self.assertEqual(qa_dict, expected_dict)

    def test_qa_from_dict(self):
        qa_data = {
            'id': "qa3",
            'question': "What is Docker?",
            'answer': "A containerization platform.",
            'company': "DevOps"
        }
        qa = QA.from_dict(qa_data)
        self.assertEqual(qa.id, "qa3")
        self.assertEqual(qa.question, "What is Docker?")
        self.assertEqual(qa.answer, "A containerization platform.")
        self.assertEqual(qa.company, "DevOps")

    def test_qa_creation_optional_id(self):
        qa = QA(question="No ID question?", answer="ID will be None.", company="TestCo")
        self.assertIsNone(qa.id)
        self.assertEqual(qa.question, "No ID question?")


if __name__ == '__main__':
    unittest.main()
