import json
import os
# import sys # Removed: Not needed for this script's path resolution
from werkzeug.security import generate_password_hash

# Determine the absolute path to the project root directory (where update_password.py is located)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Construct the path to User.json
# Assuming the app structure is ProjectRoot/TallmanChat-admin-user-qa-management/app/data/User.json
USER_FILE = os.path.join(PROJECT_ROOT, 'TallmanChat-admin-user-qa-management', 'app', 'data', 'User.json')

print(f"[DEBUG] Script path: {os.path.abspath(__file__)}")
print(f"[DEBUG] Calculated PROJECT_ROOT: {PROJECT_ROOT}")
print(f"[DEBUG] Attempting to use USER_FILE: {USER_FILE}")

def hash_password(password):
    print("[DEBUG] Hashing password...")
    hashed = generate_password_hash(password)
    print("[DEBUG] Password hashing complete.")
    return hashed

def update_user_password(email_address, new_plain_password):
    print(f"[DEBUG] update_user_password called for email: {email_address}")
    print(f"[DEBUG] Attempting to load users from: {USER_FILE}")
    try:
        print("[DEBUG] Opening USER_FILE for reading...")
        with open(USER_FILE, 'r') as f:
            print("[DEBUG] USER_FILE opened for reading. Loading JSON...")
            users_data = json.load(f)
            print("[DEBUG] JSON loaded successfully.")
    except FileNotFoundError:
        print(f"[ERROR] User file not found at {USER_FILE}")
        return False
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in user file {USER_FILE}. Details: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred while loading users: {e}")
        return False
    
    user_found = False
    print("[DEBUG] Searching for user in loaded data...")
    for user_record in users_data:
        if user_record.get('email') == email_address:
            print(f"[DEBUG] User {email_address} found. Updating password.")
            user_record['hashed_password'] = hash_password(new_plain_password)
            user_found = True
            print(f"Password hash updated in memory for user: {email_address}")
            break
    
    if not user_found:
        print(f"[INFO] User with email {email_address} not found in {USER_FILE}")
        return False
    
    print(f"[DEBUG] Attempting to save updated users data to: {USER_FILE}")
    try:
        print("[DEBUG] Opening USER_FILE for writing...")
        with open(USER_FILE, 'w') as f:
            print("[DEBUG] USER_FILE opened for writing. Dumping JSON...")
            json.dump(users_data, f, indent=4)
            print("[DEBUG] JSON dumped successfully to USER_FILE.")
        return True
    except Exception as e:
        print(f"[ERROR] Error saving updated user data to {USER_FILE}: {e}")
        return False

if __name__ == "__main__":
    target_email = "bob@example.com"
    target_new_password = "Rm2214ri#"
    
    print(f"--- Starting password update script for {target_email} ---")
    
    # Verify the USER_FILE path exists before trying to operate on it
    if not os.path.exists(USER_FILE):
        print(f"[FATAL_ERROR] The user file does not exist at the calculated path: {USER_FILE}")
        print("--- Password update script: Failed to update password. ---")
    else:
        print(f"[INFO] User file found at: {USER_FILE}")
        if update_user_password(target_email, target_new_password):
            print("--- Password update script: Password updated successfully! ---")
        else:
            print("--- Password update script: Failed to update password. ---")
