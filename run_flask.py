import os
import sys
import traceback

# Set the working directory to the nested app directory
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TallmanChat-admin-user-qa-management')
os.chdir(app_dir)
print(f"Working directory: {os.getcwd()}")

# Add the app directory to Python's path
sys.path.insert(0, app_dir)

try:
    # Import the Flask app
    from app import app
    
    # Run the Flask app
    if __name__ == "__main__":
        print("Starting Flask app on http://localhost:5000")
        app.run(host='0.0.0.0', port=5000, debug=True)
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
