import os
import sys
import subprocess
import traceback

def main():
    try:
        # Get the path to the nested app directory
        app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TallmanChat-admin-user-qa-management')
        print(f"App directory: {app_dir}")
        
        # Check if the directory exists
        if not os.path.exists(app_dir):
            print(f"Error: App directory not found at {app_dir}")
            return False
        
        # Change to the app directory
        os.chdir(app_dir)
        print(f"Changed working directory to: {os.getcwd()}")
        
        # Check if we're in a virtual environment
        in_venv = sys.prefix != sys.base_prefix
        if not in_venv:
            print("Warning: Not running in a virtual environment")
        
        # Test embedding function initialization
        try:
            print("Testing embedding function initialization...")
            from chromadb.utils import embedding_functions
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            test_embedding = ef(["This is a test sentence"])
            print(f"Embedding test successful! Shape: {len(test_embedding)} x {len(test_embedding[0])}")
        except Exception as e:
            print(f"Warning: Embedding function test failed: {e}")
            print("Continuing anyway...")
        
        # Import the app module
        print("Importing app module...")
        sys.path.insert(0, app_dir)
        from app import app
        
        # Start the Flask app
        print("Starting Flask app...")
        app.run(host='0.0.0.0', port=5000, debug=True)
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("Failed to start the application.")
        sys.exit(1)
