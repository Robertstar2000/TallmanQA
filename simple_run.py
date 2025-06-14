import os
import sys
import traceback

try:
    print("Starting simple Flask app...")
    
    # Add the app directory to Python's path
    app_path = os.path.join(os.path.dirname(__file__), 'TallmanChat-admin-user-qa-management')
    sys.path.append(app_path)
    
    # Change to the app directory to ensure templates are found
    os.chdir(app_path)
    print(f"Working directory: {os.getcwd()}")
    
    # Import the app
    from app import app
    
    # Run the app with debug enabled
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
    
except Exception as e:
    print(f"Error running Flask app: {e}")
    traceback.print_exc()
