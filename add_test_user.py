import os
import sys
import json
from werkzeug.security import generate_password_hash
from app.models import User

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# User details
test_user = {
    'id': 'test_user_1',
    'name': 'Bob',
    'email': 'bob@example.com',
    'status': 'admin',
    'password': 'Rm2214ri#'
}

def add_test_user():
    # Load existing users
    user_file = 'app/data/User.json'
    try:
        with open(user_file, 'r') as f:
            content = f.read().strip()
            if content:
                users = json.loads(content)
                if not isinstance(users, list):
                    users = [users] if users else []
            else:
                users = []
    except FileNotFoundError:
        users = []
    except json.JSONDecodeError:
        print(f"Error: {user_file} contains invalid JSON. Please check the file.")
        return

    # Check if user already exists
    user_emails = [u.get('email', '').lower() for u in users if isinstance(u, dict)]
    if test_user['email'].lower() in user_emails:
        print(f"User with email {test_user['email']} already exists.")
        return

    # Create new user
    new_user = {
        'id': test_user['id'],
        'name': test_user['name'],
        'email': test_user['email'],
        'status': test_user['status'],
        'hashed_password': generate_password_hash(test_user['password'])
    }
    users.append(new_user)

    # Save users back to file
    with open(user_file, 'w') as f:
        json.dump(users, f, indent=4)
    
    print(f"Successfully added test user:")
    print(f"Email: {test_user['email']}")
    print(f"Password: {test_user['password']}")
    print(f"Status: {test_user['status']}")

if __name__ == "__main__":
    # Create the data directory if it doesn't exist
    os.makedirs('app/data', exist_ok=True)
    add_test_user()
