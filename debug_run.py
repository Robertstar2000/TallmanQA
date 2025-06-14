import os
import sys
import traceback
import subprocess

try:
    print("Starting debug run...")
    print(f"Current working directory: {os.getcwd()}")
    
    # Check if we're in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    print(f"Running in virtual environment: {in_venv}")
    
    # Check if required packages are installed
    try:
        import flask
        print(f"Flask version: {flask.__version__}")
    except ImportError:
        print("Flask not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    
    try:
        import sentence_transformers
        print(f"Sentence-transformers version: {sentence_transformers.__version__}")
    except ImportError:
        print("Sentence-transformers not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers"])
    
    try:
        import chromadb
        print(f"ChromaDB version: {chromadb.__version__}")
    except ImportError:
        print("ChromaDB not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "chromadb"])
    
    # Add the app directory to Python's path
    app_path = os.path.join(os.path.dirname(__file__), 'TallmanChat-admin-user-qa-management')
    sys.path.append(app_path)
    print(f"Added to path: {app_path}")
    
    # Change to the app directory
    os.chdir(app_path)
    print(f"Changed working directory to: {os.getcwd()}")
    
    # Test if we can import the app
    try:
        from app import app
        print("Successfully imported app")
        
        # Check if templates directory exists and is accessible
        templates_dir = os.path.join(app_path, 'app', 'templates')
        if os.path.exists(templates_dir):
            print(f"Templates directory exists: {templates_dir}")
            template_files = os.listdir(templates_dir)
            print(f"Template files: {template_files}")
        else:
            print(f"Templates directory does not exist: {templates_dir}")
        
        # Run the app with debug output
        print("Starting Flask app with debug=True...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"Error importing or running app: {e}")
        traceback.print_exc()

except Exception as e:
    print(f"Unexpected error: {e}")
    traceback.print_exc()
