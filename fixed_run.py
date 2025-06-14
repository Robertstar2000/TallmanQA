import os
import sys
import traceback
import subprocess

# Ensure we're in a virtual environment
if sys.prefix == sys.base_prefix:
    print("Not running in a virtual environment. Please activate your virtual environment first.")
    print("Run: .\\venv\\Scripts\\activate")
    sys.exit(1)

# Check for required packages
required_packages = ['flask', 'sentence-transformers', 'chromadb', 'werkzeug']
missing_packages = []

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        missing_packages.append(package)

if missing_packages:
    print(f"Missing required packages: {', '.join(missing_packages)}")
    print("Installing missing packages...")
    for package in missing_packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"Successfully installed {package}")
        except Exception as e:
            print(f"Failed to install {package}: {e}")
            sys.exit(1)

# Set up paths correctly
try:
    # Get the absolute path to the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    print(f"Project root: {project_root}")
    
    # Path to the nested app directory
    app_dir = os.path.join(project_root, 'TallmanChat-admin-user-qa-management')
    
    # Add both directories to Python's path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    
    print(f"Python path includes: {project_root} and {app_dir}")
    
    # Change to the app directory
    os.chdir(app_dir)
    print(f"Working directory set to: {os.getcwd()}")
    
    # Verify templates directory exists
    templates_dir = os.path.join(app_dir, 'app', 'templates')
    if os.path.exists(templates_dir):
        print(f"Templates directory found: {templates_dir}")
        print(f"Template files: {os.listdir(templates_dir)}")
    else:
        print(f"WARNING: Templates directory not found at {templates_dir}")
    
    # Test embedding function initialization
    print("Testing embedding function initialization...")
    try:
        from chromadb.utils import embedding_functions
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        test_embedding = ef(["This is a test sentence"])
        print(f"Embedding test successful! Shape: {len(test_embedding)} x {len(test_embedding[0])}")
    except Exception as e:
        print(f"WARNING: Embedding function test failed: {e}")
        traceback.print_exc()
        print("Continuing anyway...")
    
    # Import and run the Flask app
    print("Importing Flask app...")
    from app import app
    
    print("Starting Flask development server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
    
except Exception as e:
    print(f"Error during setup or running Flask app: {e}")
    traceback.print_exc()
    sys.exit(1)
