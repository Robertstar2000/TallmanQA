from flask import Flask

from flask_login import LoginManager

from .utils import load_users, load_config, load_all_qa_into_chroma
from .models import User

from .utils import load_users, verify_password, load_all_qa_into_chroma # Assuming verify_password might be used by routes


app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here_change_me' # Replace with a strong, environment-based key in production


# --- Authentication Setup ---
login_manager = LoginManager(app)
login_manager.login_view = 'login' # The route for the login page

config = load_config()
ldap_manager = None  # Will be initialized only if LDAP is enabled and configured

@login_manager.user_loader
def load_user(user_id):
    loaded_users_list = load_users()
    for user_obj in loaded_users_list:
        if user_obj.id == user_id:
            return user_obj
    return None

# --- LDAP Configuration ---
# This part configures the LDAP manager from your config file
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
    ldap_manager = LDAP3LoginManager(app) # Initialize and assign to the module-level variable

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

=======

# Import routes after app initialization to avoid circular imports
from . import routes

print("Attempting to load all Q&A data into ChromaDB at startup...")
try:

    # The EmbeddingManager in utils.py will be used to get or create the embedding function as needed
    # This ensures we always have an embedding function available when needed

    # Make sure sentence_transformer_ef is initialized in utils before this is called
    # or that load_all_qa_into_chroma handles its absence.
    # Based on previous utils.py, it should handle it.

    load_all_qa_into_chroma()
    print("ChromaDB loading process initiated. Check console for details and completion.")
except Exception as e:
    print(f"Error during initial loading of data into ChromaDB: {e}")
    print("The application will continue, but Q&A search functionality might be impaired.")

# The following is for running the app directly using `python -m app`
# For development only. Use a WSGI server in production.
if __name__ == '__main__':
    # This allows running with `python -m app`
    # However, typically app.py or a run.py is used.
    # For this project structure, let's assume app.py will be the main entry point.
    # So, this block might be removed from here if app.py is the designated runner.
    # For now, keeping it as per instructions that __init__ could make app runnable.
    print("Running Flask app directly from __init__.py (development mode)")
    app.run(debug=True, port=5000)
