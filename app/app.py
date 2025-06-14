from app import app  # Imports the app instance from app/__init__.py

if __name__ == '__main__':
    # In a production environment, use a WSGI server like Gunicorn or Waitress.
    # For development:
    # The host '0.0.0.0' makes the server accessible externally, useful for testing in VMs/containers.
    # Debug mode should be False in production.
    print("Starting Flask development server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
