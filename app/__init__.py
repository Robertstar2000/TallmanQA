from flask import Flask
from .utils import load_users, verify_password, load_all_qa_into_chroma # Assuming verify_password might be used by routes

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here_change_me' # Replace with a strong, environment-based key in production

# Import routes after app initialization to avoid circular imports
from . import routes

print("Attempting to load all Q&A data into ChromaDB at startup...")
try:
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
