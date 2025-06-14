import os
import sys
import subprocess

REQUIREMENTS_FILE = os.path.join(os.path.dirname(__file__), 'requirements.txt')

# Check if running inside a virtual environment
if sys.prefix == sys.base_prefix:
    print("[ERROR] Please activate your virtual environment before running this script.")
    print("[INFO] Run: .\\venv\\Scripts\\activate (on Windows) or source venv/bin/activate (on Mac/Linux)")
    sys.exit(1)

# Install dependencies if needed BEFORE importing anything else
try:
    # Check for key dependencies
    import flask
    import chromadb
    import sentence_transformers
    print("[INFO] All required packages are installed.")

except ImportError as e:
    print(f"[INFO] Installing dependencies from requirements.txt... ({e})")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', REQUIREMENTS_FILE])
    print("[INFO] Dependencies installed.")

# Simple check of sentence-transformers before importing the app
try:
    from sentence_transformers import SentenceTransformer
    print("[INFO] Successfully imported sentence-transformers.")

    # Just try to load a test model to verify it works
    model = SentenceTransformer('all-MiniLM-L6-v2') # This can take a moment on first run
    print("[SUCCESS] Successfully loaded the sentence transformer model.")

    # Quick test to ensure it works
    test_embedding = model.encode(["test sentence"])
    if test_embedding is None or len(test_embedding) == 0:
        print("[ERROR] SentenceTransformer model failed to generate embeddings!")
        sys.exit(1)
    else:
        print("[SUCCESS] Embedding generation test successful!")

except Exception as e:
    print(f"[FATAL] Error testing sentence-transformers: {e}")
    print("[INFO] Try reinstalling with: pip install -U sentence-transformers")
    sys.exit(1)

# Only import the app after dependencies are properly checked
print("[INFO] About to import 'app' from 'app' module...")
from app import app # This is where ChromaDB initialization happens via app/__init__.py
print("[INFO] Successfully imported 'app' from 'app' module.")

if __name__ == '__main__':
    print("[INFO] Entered __main__ block.")
    print("[INFO] Starting Flask development server (debug=True by default with reloader)...")
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
        print("[INFO] app.run() completed. This typically means the server stopped or failed to start and block.")
    except Exception as e_run:
        print(f"[ERROR] Exception during app.run(): {e_run}")
        import traceback
        traceback.print_exc()
    print("[INFO] End of __main__ block (after app.run call).")
else:
    print("[INFO] Script was imported, not run directly.")

print("[INFO] End of run.py script (reached after __main__ or import).")
