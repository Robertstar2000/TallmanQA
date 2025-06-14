import os
import sys
import subprocess

# Check if running in virtual environment
if sys.prefix == sys.base_prefix:
    print("Not running in a virtual environment!")
    print("Please activate your virtual environment first with:")
    print("  .\\venv\\Scripts\\activate")
    sys.exit(1)

# Check for required packages
try:
    import flask
    import sentence_transformers
    import chromadb
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Installing requirements...")
    requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_file):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
    else:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "sentence-transformers", "chromadb"])

# The simplest approach: run the Flask app directly from the nested directory
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TallmanChat-admin-user-qa-management')

print(f"Changing to app directory: {app_dir}")
os.chdir(app_dir)

# Run the Flask app using the Python interpreter
print("Starting Flask app...")
subprocess.call([sys.executable, "-m", "flask", "--app", "app", "run", "--host=0.0.0.0", "--port=5000", "--debug"])
