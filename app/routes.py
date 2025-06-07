from functools import wraps
from flask import render_template, request, redirect, url_for, session, jsonify, flash
from app import app, load_users
from app.models import User, QA # QA model needed for type hinting if not direct use
from app.utils import (
    verify_password,
    query_collection,
    get_llm_answer,
    get_corrected_llm_answer,
    append_qa_pair,
    get_or_create_collection,
    format_snippets_for_llm # For formatting snippets for display
)

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('ask_ai_get')) # Redirect to GET version of ask_ai
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Email and password are required.', 'warning')
            # For POST to /login, usually an API endpoint, so JSON is good.
            return jsonify({'status': 'error', 'message': 'Email and password required'}), 400

        users = load_users()
        user_data = next((u for u in users if u.email == email), None)

        if user_data and user_data.check_password(password):
            session['user_id'] = user_data.id
            session['status'] = user_data.status
            session['name'] = user_data.name
            flash('Login successful!', 'success')
            return jsonify({'status': 'success', 'message': 'Login successful', 'user_status': user_data.status, 'redirect_url': url_for('ask_ai_get')})
        else:
            flash('Invalid email or password.', 'danger')
            return jsonify({'status': 'error', 'message': 'Invalid email or password'}), 401

    if 'user_id' in session:
        return redirect(url_for('ask_ai_get'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('status', None)
    session.pop('name', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            if request.headers.get("X-Requested-With") == "XMLHttpRequest": # Check if AJAX
                 return jsonify({'status': 'error', 'message': 'Login required', 'redirect_url': url_for('login', next=request.url)}), 401
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in.', 'warning')
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({'status': 'error', 'message': 'Login required', 'redirect_url': url_for('login', next=request.url)}), 401
            return redirect(url_for('login', next=request.url))
        if session.get('status') != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({'status': 'error', 'message': 'Admin access required'}), 403
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Renamed placeholder ask_ai to ask_ai_get for clarity
@app.route('/ask', methods=['GET'])
@login_required
def ask_ai_get():
    return render_template('screen1.html')

@app.route('/api/ask', methods=['POST']) # API endpoint for asking questions
@login_required
def ask_ai_post():
    data = request.json
    user_question = data.get('user_question')
    company = data.get('company')
    question_type = data.get('question_type')

    if not all([user_question, company, question_type]):
        return jsonify({'status': 'error', 'message': 'Missing required fields (question, company, or type).'}), 400

    # Basic validation for company and question_type (can be expanded)
    valid_companies = ["Tallman", "MCR", "Bradley"]
    # PROMPT_TEMPLATES keys can be fetched from utils/Type.py for dynamic validation if needed
    valid_question_types = ["Product", "Sales", "General Help", "Tutorial", "Default"]
    if company not in valid_companies:
        return jsonify({'status': 'error', 'message': f'Invalid company: {company}.'}), 400
    if question_type not in valid_question_types:
        return jsonify({'status': 'error', 'message': f'Invalid question type: {question_type}.'}), 400

    try:
        collection = get_or_create_collection(company)
        retrieved_snippets_dicts = query_collection(collection, user_question, n_results=3)

        llm_answer = get_llm_answer(user_question, company, question_type, retrieved_snippets_dicts)

        # format_snippets_for_llm expects list of dicts, which retrieved_snippets_dicts is.
        display_snippets = format_snippets_for_llm(retrieved_snippets_dicts)

        if "Error generating answer from LLM" in llm_answer or "OpenAI API key not configured" in llm_answer :
             return jsonify({
                'status': 'error',
                'message': llm_answer,
                'user_question': user_question,
                'retrieved_snippets_formatted': display_snippets,
                'raw_snippets': retrieved_snippets_dicts,
                'company': company,
                'question_type': question_type
            }), 500

        return jsonify({
            'status': 'success',
            'user_question': user_question,
            'answer': llm_answer,
            'retrieved_snippets_formatted': display_snippets,
            'raw_snippets': retrieved_snippets_dicts,
            'company': company,
            'question_type': question_type
        })
    except RuntimeError as r_e: # Catch errors like sentence transformer not initialized
        app.logger.error(f"Runtime error in /api/ask: {r_e}")
        return jsonify({'status': 'error', 'message': str(r_e)}), 500
    except Exception as e:
        app.logger.error(f"Exception in /api/ask: {e}")
        return jsonify({'status': 'error', 'message': 'An internal error occurred while processing your question.'}), 500


@app.route('/correct_answer_page', methods=['GET']) # Placeholder if a dedicated page is needed
@admin_required # Or login_required if any user can suggest corrections via this page
def correct_answer_page_get():
    # This page might be pre-filled if navigated from screen1 with context
    original_question = request.args.get('original_question')
    incorrect_answer = request.args.get('incorrect_answer')
    company = request.args.get('company')
    return render_template('screen2.html',
                           original_question=original_question,
                           incorrect_answer=incorrect_answer,
                           company=company)

@app.route('/api/correct_answer', methods=['POST'])
@admin_required # Only admins can directly correct and update the knowledge base
def correct_answer_post():
    data = request.json
    original_question = data.get('original_question')
    incorrect_answer = data.get('incorrect_answer')
    user_correction_text = data.get('user_correction_text')
    company = data.get('company')

    if not all([original_question, incorrect_answer, user_correction_text, company]):
        return jsonify({'status': 'error', 'message': 'Missing required fields for correction.'}), 400

    valid_companies = ["Tallman", "MCR", "Bradley"]
    if company not in valid_companies:
        return jsonify({'status': 'error', 'message': f'Invalid company: {company}.'}), 400

    try:
        new_answer = get_corrected_llm_answer(original_question, incorrect_answer, user_correction_text, company)

        if "Error generating corrected answer from LLM" in new_answer or "OpenAI API key not configured" in new_answer:
            return jsonify({'status': 'error', 'message': new_answer}), 500

        # Append the corrected Q&A pair. is_update=True marks it.
        # append_qa_pair handles file writing and ChromaDB update.
        qa_item = append_qa_pair(company, original_question, new_answer, is_update=True)

        return jsonify({
            'status': 'success',
            'message': 'Answer corrected. The new Q&A has been added to the knowledge base and ChromaDB.',
            'corrected_question': original_question,
            'new_answer': new_answer,
            'qa_id': qa_item.id
        })
    except RuntimeError as r_e:
        app.logger.error(f"Runtime error in /api/correct_answer: {r_e}")
        return jsonify({'status': 'error', 'message': str(r_e)}), 500
    except Exception as e:
        app.logger.error(f"Exception in /api/correct_answer: {e}")
        return jsonify({'status': 'error', 'message': 'An internal error occurred while correcting the answer.'}), 500


@app.route('/manage_users', methods=['GET'])
@admin_required
def manage_users():
    users = load_users()
    return render_template('screen3.html', users=[user.to_dict() for user in users])

# Placeholder for actual user management API endpoints (add, edit, delete)
@app.route('/api/users', methods=['POST'])
@admin_required
def api_add_user():
    # Logic to add a user will be here
    return jsonify({'status': 'not_implemented', 'message': 'Add user functionality not yet implemented.'}), 501

@app.route('/api/users/<user_id>', methods=['PUT', 'DELETE'])
@admin_required
def api_manage_user(user_id):
    if request.method == 'PUT':
        # Logic to edit user user_id
        return jsonify({'status': 'not_implemented', 'message': f'Edit user {user_id} not yet implemented.'}), 501
    elif request.method == 'DELETE':
        # Logic to delete user user_id
        return jsonify({'status': 'not_implemented', 'message': f'Delete user {user_id} not yet implemented.'}), 501

# Renamed old placeholders to avoid conflicts
@app.route('/ask_ai_old_placeholder')
@login_required
def ask_ai_placeholder():
    return "Ask AI Page (Screen 1) - Requires Login"

@app.route('/correct_answer_old_placeholder')
@login_required # Or admin_required depending on policy
def correct_answer_placeholder():
    return "Correct Answer Page (Screen 2) - Requires Login/Admin"
