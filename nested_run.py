import os
import sys
import subprocess

# Get the path to the nested app directory
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TallmanChat-admin-user-qa-management')
print(f"App directory: {app_dir}")

# Check if the directory exists
if not os.path.exists(app_dir):
    print(f"Error: App directory not found at {app_dir}")
    sys.exit(1)

# Change to the app directory
os.chdir(app_dir)
print(f"Changed working directory to: {os.getcwd()}")

# Run the app directly from the nested directory
try:
    print("Running the Flask app...")
    # Use the Python executable from the current environment
    result = subprocess.run([sys.executable, "run.py"], 
                           cwd=app_dir,
                           capture_output=True, 
                           text=True)
    
    print(f"Exit code: {result.returncode}")
    print(f"Output: {result.stdout}")
    
    if result.stderr:
        print(f"Error: {result.stderr}")
        
except Exception as e:
    print(f"Error running Flask app: {e}")
