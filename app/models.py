from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import UserMixin

class User(UserMixin):
=======

class User:

    def __init__(self, id, name, email, status, hashed_password):
        self.id = id
        self.name = name
        self.email = email
        self.status = status
        self.hashed_password = hashed_password

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)


    def is_admin(self):
        return self.status == 'admin'

in
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'status': self.status,
            'hashed_password': self.hashed_password
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            email=data.get('email'),
            status=data.get('status'),
            hashed_password=data.get('hashed_password')
        )

class QA:
    def __init__(self, question: str, answer: str, company: str, id: str = None):
        self.question = question
        self.answer = answer
        self.company = company
        self.id = id

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'company': self.company
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            question=data.get('question'),
            answer=data.get('answer'),
            company=data.get('company'),
            id=data.get('id')
        )
