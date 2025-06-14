# Authentication System Documentation

This document provides a comprehensive overview of the authentication system used in the TallmanChat Admin User QA Management application, including login, signup, and LDAP integration.

## Table of Contents

1. [Overview](#overview)
2. [User Model](#user-model)
3. [Login Process](#login-process)
4. [User Registration](#user-registration)
5. [LDAP Integration](#ldap-integration)
6. [User Management](#user-management)
7. [Security Considerations](#security-considerations)

## Overview

The application implements a dual authentication system that supports both local user authentication and LDAP (Lightweight Directory Access Protocol) integration. This allows organizations to either manage users locally or connect to an existing directory service.

## User Model

The application uses a `User` class that implements Flask-Login's `UserMixin` for session management.

```python
# From app/models.py
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin):
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
```

Key features of the User model:
- Uses Werkzeug's security functions for password hashing and verification
- Supports user roles through the `status` field (admin or regular user)
- Provides serialization/deserialization methods for JSON storage
- Implements Flask-Login's UserMixin for session management

## Login Process

### Login UI

The login page is a simple form that collects email and password:

```html
<!-- From app/templates/login.html -->
<form id="loginForm" method="POST" action="{{ url_for('login') }}">
    <div>
        <label for="email">Email:</label>
        <input type="email" id="email" name="email" required>
    </div>
    <div>
        <label for="password">Password:</label>
        <input type="password" id="password" name="password" required>
    </div>
    <div>
        <input type="submit" value="Login">
    </div>
</form>
```

The form is enhanced with JavaScript to provide asynchronous login functionality:

```javascript
// From app/templates/login.html
document.getElementById('loginForm').addEventListener('submit', async function(event) {
    event.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const loginMessageDiv = document.getElementById('loginMessage');
    loginMessageDiv.innerHTML = ''; // Clear previous messages

    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);

    try {
        const response = await fetch("{{ url_for('login') }}", {
            method: 'POST',
            body: new URLSearchParams(formData) // Send as form data
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            loginMessageDiv.innerHTML = `<p style="color:green">${data.message}</p>`;
            if (data.redirect_url) {
                window.location.href = data.redirect_url;
            } else {
                // Fallback if no redirect URL is provided
                window.location.href = "{{ url_for('index') }}";
            }
        } else {
            loginMessageDiv.innerHTML = `<p style="color:red;">${data.message || 'Login failed.'}</p>`;
        }
    } catch (error) {
        console.error('Login request failed:', error);
        loginMessageDiv.innerHTML = `<p style="color:red;">An error occurred during login. Please try again.</p>`;
    }
});
```

### Login Backend

The login route handles both GET requests (to display the login form) and POST requests (to process login attempts):

```python
# From app/routes.py
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('ask_ai_get'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return jsonify({'status': 'error', 'message': 'Email and password are required.'}), 400

        user_to_login = None
        auth_method = 'local'

        # Try LDAP first if enabled
        if config.get('ldap', {}).get('enabled', False):
            try:
                response = ldap_manager.authenticate(email, password)
                if response.status.value == 0:  # LDAP_SUCCESS
                    users_list_ldap = load_users()
                    user_to_login = None
                    for u_ldap in users_list_ldap:
                        if u_ldap.email == email:
                            user_to_login = u_ldap
                            break
                    auth_method = 'LDAP'
                    if not user_to_login:
                        return jsonify({'status': 'error', 'message': 'LDAP login successful, but no local user profile found.'}), 403
            except Exception as e:
                print(f"[ERROR] LDAP connection failed: {e}")
                # Fall through to local auth if LDAP server is down
        
        # Fallback to local authentication
        if not user_to_login:
            users_list_for_local_auth = load_users()
            local_user = None
            for user_candidate in users_list_for_local_auth:
                if user_candidate.email == email:
                    local_user = user_candidate
                    break
            if local_user and local_user.check_password(password):
                user_to_login = local_user
                auth_method = 'local'
        
        if user_to_login:
            login_user(user_to_login)
            return jsonify({'status': 'success', 'message': f'{auth_method.capitalize()} login successful!', 'redirect_url': url_for('ask_ai_get')})
        else:
            message = 'Invalid email or password.'
            return jsonify({'status': 'error', 'message': message}), 401

    return render_template('login.html')
```

The login process follows these steps:
1. Check if the user is already authenticated, redirect if so
2. Validate that email and password were provided
3. If LDAP is enabled, attempt LDAP authentication first
4. If LDAP authentication succeeds, look for a matching local user profile
5. If LDAP authentication fails or is disabled, fall back to local authentication
6. If authentication succeeds, log the user in and redirect to the main application
7. If authentication fails, return an error message

## User Registration

Unlike many applications, this system does not provide self-registration. New users must be added by an administrator.

### Adding Users Programmatically

The application includes a script (`add_test_user.py`) that demonstrates how to add a user programmatically:

```python
# From add_test_user.py
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
```

### User Storage

Users are stored in a JSON file (`app/data/User.json`). The application provides utility functions to load and save users:

```python
# From app/utils.py
def load_users() -> list[User]:
    try:
        with open(USER_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            if not data:
                return []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing {USER_FILE}: {e}")
        return []

    users = []
    if isinstance(data, list):
        user_data_list = data
    elif isinstance(data, dict):
        user_data_list = [data]
    else:
        return []

    for user_data in user_data_list:
        if user_data:  # Only process non-empty user data
            try:
                users.append(User.from_dict(user_data))
            except Exception as e:
                print(f"Error creating user from data {user_data}: {e}")
    
    return users

def save_users(users: list[User]) -> None:
    with open(USER_FILE, 'w') as f:
        json.dump([user.to_dict() for user in users], f, indent=4)
```

## LDAP Integration

The application supports LDAP authentication through the Flask-LDAP3-Login extension.

### LDAP Configuration

LDAP settings are stored in the application's configuration file (`app/data/config.json`):

```json
{
    "ldap": {
        "enabled": false,
        "server": "ldap://your-ldap-server.com",
        "port": 389,
        "use_ssl": false,
        "base_dn": "ou=users,dc=example,dc=com",
        "user_dn": "ou=users",
        "group_dn": "ou=groups",
        "bind_user_dn": "cn=admin,dc=example,dc=com",
        "bind_user_password": "",
        "user_rdn_attr": "cn",
        "user_login_attr": "uid",
        "user_object_filter": "(objectClass=inetOrgPerson)",
        "group_object_filter": "(objectClass=groupOfNames)",
        "group_member_attr": "member"
    }
}
```

### LDAP Initialization

The LDAP manager is initialized during application startup if LDAP is enabled:

```python
# From app/__init__.py
# --- LDAP Configuration ---
if config.get('ldap', {}).get('enabled', False) and config.get('ldap', {}).get('server'):
    # LDAP is enabled and a server is specified in the config.
    # Set Flask app configurations for LDAP
    app.config['LDAP_HOST'] = config['ldap'].get('server')
    app.config['LDAP_PORT'] = config['ldap'].get('port', 389)
    app.config['LDAP_USE_SSL'] = config['ldap'].get('use_ssl', False)
    app.config['LDAP_BASE_DN'] = config['ldap'].get('base_dn')
    app.config['LDAP_USER_DN'] = config['ldap'].get('user_dn', 'ou=users')
    app.config['LDAP_GROUP_DN'] = config['ldap'].get('group_dn', 'ou=groups')
    app.config['LDAP_USER_RDN_ATTR'] = config['ldap'].get('user_rdn_attr', 'cn')
    app.config['LDAP_USER_LOGIN_ATTR'] = config['ldap'].get('user_login_attr', 'uid')
    app.config['LDAP_BIND_USER_DN'] = config['ldap'].get('bind_user_dn')
    app.config['LDAP_BIND_USER_PASSWORD'] = config['ldap'].get('bind_user_password')
    app.config['LDAP_USER_OBJECT_FILTER'] = config['ldap'].get('user_object_filter', '(objectClass=inetOrgPerson)')
    app.config['LDAP_GROUP_OBJECT_FILTER'] = config['ldap'].get('group_object_filter', '(objectClass=groupOfNames)')
    app.config['LDAP_GROUP_MEMBERS_ATTR'] = config['ldap'].get('group_member_attr', 'member')

    # Dynamically import and initialize LDAP3LoginManager
    from flask_ldap3_login import LDAP3LoginManager
    ldap_manager = LDAP3LoginManager(app)

    @ldap_manager.save_user
    def save_user(dn, username, data, memberships):
        from .utils import save_users, load_users # Import locally
        users = load_users()
        mail_attr = data.get('mail')
        if isinstance(mail_attr, list) and mail_attr:
            user_email = mail_attr[0]
        else:
            print(f"Warning: LDAP data for user {username} missing 'mail' attribute or not a list. Using username as ID.")
            user_email = username 

        user = users.get(user_email)
        if user is None:
            user = User(id=user_email, username=username, is_active=True)
            users[user_email] = user
            save_users(users)
            
        return user
```

### LDAP Authentication Flow

When a user attempts to log in and LDAP is enabled:

1. The application first tries to authenticate the user against the LDAP server
2. If LDAP authentication succeeds, the application looks for a matching local user profile
3. If a matching local profile is found, the user is logged in
4. If no matching profile is found, an error is returned
5. If LDAP authentication fails or an error occurs, the application falls back to local authentication

## User Management

Administrators can manage users through a dedicated interface (`screen3.html`).

### User Management UI

The user management interface allows administrators to:
- View all existing users
- Add new users
- Edit existing users
- Delete users

```html
<!-- From app/templates/screen3.html (excerpt) -->
<div id="userManagementArea">
    <h2>Existing Users</h2>
    <table class="table table-striped" id="usersTable">
        <thead>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% if users %}
                {% for user in users %}
                <tr data-user-id="{{ user.id }}">
                    <td>{{ user.id }}</td>
                    <td>{{ user.name }}</td>
                    <td>{{ user.email }}</td>
                    <td>{{ user.status }}</td>
                    <td>
                        <button class="btn btn-sm btn-primary edit-user-btn" data-id="{{ user.id }}" data-name="{{ user.name }}" data-email="{{ user.email }}" data-status="{{ user.status }}">Edit</button>
                        <button class="btn btn-sm btn-danger delete-user-btn" data-id="{{ user.id }}">Delete</button>
                    </td>
                </tr>
                {% endfor %}
            {% else %}
            <tr>
                <td colspan="5">No users found.</td>
            </tr>
            {% endif %}
        </tbody>
    </table>

    <hr>
    <!-- "Add User" Button to toggle form visibility -->
    <button type="button" class="btn btn-success mb-3" id="showAddUserFormBtn">Add New User</button>

    <!-- Add User Form (Initially Hidden) -->
    <div id="addUserModal" style="display:none; border:1px solid #ccc; padding:20px; margin-bottom:20px; background-color:#f9f9f9;">
        <h2>Add New User</h2>
        <form id="addUserForm">
            <div class="form-group mb-2">
                <label for="add_user_name">Name:</label>
                <input type="text" class="form-control" id="add_user_name" name="name" required>
            </div>
            <div class="form-group mb-2">
                <label for="add_user_email">Email:</label>
                <input type="email" class="form-control" id="add_user_email" name="email" required>
            </div>
            <div class="form-group mb-2">
                <label for="add_user_password">Password:</label>
                <input type="password" class="form-control" id="add_user_password" name="password" required>
            </div>
            <div class="form-group mb-2">
                <label for="add_user_status">Status:</label>
                <select class="form-control" id="add_user_status" name="status">
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary">Create User</button>
            <button type="button" class="btn btn-secondary" id="cancelAddUserBtn">Cancel</button>
        </form>
    </div>
</div>
```

### User Management API

The application provides API endpoints for user management:

```python
# From app/routes.py
@app.route('/api/users', methods=['POST'])
@admin_required
def api_add_user():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    status = data.get('status', 'user')  # Default to 'user'

    if not all([name, email, password]):
        return jsonify({'status': 'error', 'message': 'Missing required fields: name, email, password'}), 400

    if status not in ['user', 'admin']:
        return jsonify({'status': 'error', 'message': "Invalid status. Must be 'user' or 'admin'."}), 400

    users = load_users()
    if any(u.email == email for u in users):
        return jsonify({'status': 'error', 'message': 'User with this email already exists'}), 409

    new_user_id = uuid.uuid4().hex
    user = User(id=new_user_id, name=name, email=email, status=status)
    user.set_password(password)  # Hash the password

    users.append(user)
    save_users(users)

    user_data = user.to_dict()
    del user_data['password_hash'] # Ensure password hash is not returned

    return jsonify({'status': 'success', 'message': 'User added successfully', 'user': user_data}), 201

@app.route('/api/users/<user_id>', methods=['PUT', 'DELETE'])
@admin_required
def api_manage_user(user_id):
    users = load_users()
    user = next((u for u in users if u.id == user_id), None)

    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400

        # Update name, email, status if provided
        user.name = data.get('name', user.name)
        new_email = data.get('email')
        user.status = data.get('status', user.status)

        if user.status not in ['user', 'admin']:
            return jsonify({'status': 'error', 'message': "Invalid status. Must be 'user' or 'admin'."}), 400

        # Check for email conflict if email is being changed
        if new_email and new_email != user.email:
            if any(u.email == new_email for u in users if u.id != user_id):
                return jsonify({'status': 'error', 'message': 'Email already in use by another user'}), 409
            user.email = new_email

        # Update password if provided and not empty
        password = data.get('password')
        if password: # Check if password is not None and not an empty string
            user.set_password(password)

        save_users(users)
        user_data = user.to_dict()
        del user_data['password_hash'] # Ensure password hash is not returned
        return jsonify({'status': 'success', 'message': 'User updated successfully', 'user': user_data}), 200

    elif request.method == 'DELETE':
        users.remove(user)
        save_users(users)
        return jsonify({'status': 'success', 'message': 'User deleted successfully'}), 200
```

## Security Considerations

The authentication system implements several security best practices:

1. **Password Hashing**: Passwords are never stored in plain text. The application uses Werkzeug's `generate_password_hash` and `check_password_hash` functions, which implement secure password hashing.

2. **HTTPS Recommendation**: While not enforced in the code, the application should be deployed behind HTTPS in production to protect credentials in transit.

3. **Role-Based Access Control**: The application implements a simple role-based access control system with the `@admin_required` decorator:

```python
# From app/routes.py
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if not current_user.is_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('ask_ai_get'))
        return f(*args, **kwargs)
    return decorated_function
```

4. **LDAP Integration**: When enabled, LDAP provides an additional layer of security by delegating authentication to an enterprise directory service.

5. **Session Management**: The application uses Flask-Login for session management, which handles secure cookie-based sessions.

6. **Input Validation**: The application validates user input on both the client and server sides to prevent injection attacks.

7. **Error Handling**: Authentication errors are handled gracefully without revealing sensitive information.
