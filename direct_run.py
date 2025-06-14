import os
import sys
import traceback

try:
    # Change to the nested app directory first
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TallmanChat-admin-user-qa-management')
    os.chdir(app_dir)
    print(f"Working directory: {os.getcwd()}")
    
    # Add the app directory to Python's path
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    
    # Import Flask and create a simple test app to verify it works
    from flask import Flask, render_template
    
    # Create a simple test app
    test_app = Flask(__name__, 
                    template_folder=os.path.join(app_dir, 'app', 'templates'),
                    static_folder=os.path.join(app_dir, 'app', 'static'))
    
    @test_app.route('/test')
    def test():
        return "Flask is working!"
    
    @test_app.route('/test-template')
    def test_template():
        try:
            return render_template('login.html')
        except Exception as e:
            return f"Error rendering template: {str(e)}"
    
    print("Starting test Flask app...")
    test_app.run(host='0.0.0.0', port=5001, debug=True)
    
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
