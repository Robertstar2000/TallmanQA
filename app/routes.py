from functools import wraps
from flask import render_template, request, redirect, url_for, session, jsonify, flash
from app import app, load_users
from app.models import User, QA # QA model needed for type hinting if not direct use
import uuid
from app.utils import (
    save_users,
    verify_password,
    query_collection,
    get_llm_answer,
    get_corrected_llm_answer,
    append_qa_pair,
    get_or_create_collection,
    format_snippets_for_llm, # For formatting snippets for display
    load_qa_data, # For downloading Q&A data
    append_qa_pair # For uploading Q&A data
)
import json # For parsing uploaded JSON

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
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    status = data.get('status', 'user')  # Default to 'user'

    if not all([name, email, password]):
        return jsonify({'status': 'error', 'message': 'Missing required fields: name, email, password'}), 400

    if status not in ['user', 'admin']:
        return jsonify({'status': 'error', 'message': "Invalid status. Must be 'user' or 'admin'."}), 400

    users = load_users()
    if any(u.email == email for u in users):
        return jsonify({'status': 'error', 'message': 'User with this email already exists'}), 409

    new_user_id = uuid.uuid4().hex
    user = User(id=new_user_id, name=name, email=email, status=status)
    user.set_password(password)  # Hash the password

    users.append(user)
    save_users(users)

    user_data = user.to_dict()
    del user_data['password_hash'] # Ensure password hash is not returned

    return jsonify({'status': 'success', 'message': 'User added successfully', 'user': user_data}), 201

@app.route('/api/users/<user_id>', methods=['PUT', 'DELETE'])
@admin_required
def api_manage_user(user_id):
    users = load_users()
    user = next((u for u in users if u.id == user_id), None)

    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400

        # Update name, email, status if provided
        user.name = data.get('name', user.name)
        new_email = data.get('email')
        user.status = data.get('status', user.status)

        if user.status not in ['user', 'admin']:
            return jsonify({'status': 'error', 'message': "Invalid status. Must be 'user' or 'admin'."}), 400

        # Check for email conflict if email is being changed
        if new_email and new_email != user.email:
            if any(u.email == new_email for u in users if u.id != user_id):
                return jsonify({'status': 'error', 'message': 'Email already in use by another user'}), 409
            user.email = new_email

        # Update password if provided and not empty
        password = data.get('password')
        if password: # Check if password is not None and not an empty string
            user.set_password(password)

        save_users(users)
        user_data = user.to_dict()
        del user_data['password_hash'] # Ensure password hash is not returned
        return jsonify({'status': 'success', 'message': 'User updated successfully', 'user': user_data}), 200

    elif request.method == 'DELETE':
        users.remove(user)
        save_users(users)
        return jsonify({'status': 'success', 'message': 'User deleted successfully'}), 200 # Or 204 No Content

# Renamed old placeholders to avoid conflicts
@app.route('/ask_ai_old_placeholder')
@login_required
def ask_ai_placeholder():
    return "Ask AI Page (Screen 1) - Requires Login"

@app.route('/correct_answer_old_placeholder')
@login_required # Or admin_required depending on policy
def correct_answer_placeholder():
    return "Correct Answer Page (Screen 2) - Requires Login/Admin"


@app.route('/admin/download_qa/<company_name>', methods=['GET'])
@admin_required
def download_qa_file(company_name):
    # These should ideally be sourced from a config or from app.utils where file paths are defined
    valid_companies = ["Tallman", "MCR", "Bradley"]
    if company_name not in valid_companies:
        return jsonify({'status': 'error', 'message': 'Invalid or unsupported company name'}), 400

    try:
        qa_data_list = load_qa_data(company_name) # This returns list[QA]

        # load_qa_data returns an empty list if file not found or empty, which is acceptable.
        # No specific error needs to be raised here for that case unless behavior change is desired.

        qa_data_dicts = [qa.to_dict() for qa in qa_data_list]

        response = jsonify(qa_data_dicts)
        response.headers["Content-Disposition"] = f"attachment; filename={company_name}_qa_data.json"
        # jsonify should set Content-Type to application/json automatically
        return response, 200

    except ValueError as ve:
        # This might occur if load_qa_data internally raises ValueError for bad company name,
        # though current utils.get_qa_filepath raises FileNotFoundError handled by load_qa_data.
        # Adding for robustness in case utils changes.
        app.logger.error(f"ValueError during Q&A download for {company_name}: {ve}")
        return jsonify({'status': 'error', 'message': str(ve)}), 400
    except Exception as e:
        # Log the exception for debugging
        app.logger.error(f"Unexpected error generating Q&A download for {company_name}: {e}")
        return jsonify({'status': 'error', 'message': 'An internal error occurred while generating the Q&A file.'}), 500


ALLOWED_EXTENSIONS_QA_UPLOAD = {'json'}

def allowed_file_qa(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_QA_UPLOAD

@app.route('/admin/upload_qa/<company_name>', methods=['POST'])
@admin_required
def upload_qa_file(company_name):
    valid_companies = ["Tallman", "MCR", "Bradley"] # Ideally, sync with utils or config
    if company_name not in valid_companies:
        return jsonify({'status': 'error', 'message': 'Invalid or unsupported company name'}), 400

    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected for uploading'}), 400

    if not (file and allowed_file_qa(file.filename)):
        return jsonify({'status': 'error', 'message': 'Invalid file type. Only .json files are allowed.'}), 400

    try:
        file_content = file.read().decode('utf-8')
        data = json.loads(file_content)
    except UnicodeDecodeError:
        return jsonify({'status': 'error', 'message': 'File content is not valid UTF-8.'}), 400
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': 'Invalid JSON format in the uploaded file.'}), 400
    except Exception as e:
        app.logger.error(f"Error reading or parsing Q&A upload for {company_name}: {e}")
        return jsonify({'status': 'error', 'message': f'Error reading or parsing file: {str(e)}'}), 400

    if not isinstance(data, list):
        return jsonify({'status': 'error', 'message': 'Invalid JSON content. Expected a list of Q&A objects.'}), 400

    processed_count = 0
    errors = []

    for index, item in enumerate(data):
        if not isinstance(item, dict) or 'question' not in item or 'answer' not in item:
            errors.append(f"Item {index+1}: Invalid format. Must be a dict with 'question' and 'answer' keys. Item: {str(item)[:100]}")
            continue

        question = item['question']
        answer = item['answer']

        if not question or not isinstance(question, str) or not answer or not isinstance(answer, str) :
             errors.append(f"Item {index+1}: Question and Answer must be non-empty strings. Question: '{str(question)[:50]}', Answer: '{str(answer)[:50]}'")
             continue

        try:
            # append_qa_pair's is_update defaults to False, which is correct for new additions.
            append_qa_pair(company_name, question, answer)
            processed_count += 1
        except Exception as e:
            app.logger.error(f"Error appending Q&A for {company_name} from uploaded file (item {index+1}): {e} on item: {question[:50]}")
            errors.append(f"Item {index+1} ('{question[:50]}...'): Error processing - {str(e)}")

    if errors:
        if processed_count > 0:
            # Partial success
            return jsonify({
                'status': 'partial_success',
                'message': f'Processed {processed_count} Q&A pairs for {company_name}. Encountered {len(errors)} errors.',
                'errors': errors,
                'processed_count': processed_count,
                'error_count': len(errors)
            }), 207 # Multi-Status
        else:
            # All items failed
            return jsonify({
                'status': 'error',
                'message': f'Failed to process any Q&A pairs for {company_name}. Encountered {len(errors)} errors.',
                'errors': errors,
                'processed_count': 0,
                'error_count': len(errors)
            }), 400

    if processed_count == 0 and not data: # Empty JSON array was uploaded
         return jsonify({
            'status': 'success',
            'message': 'No Q&A pairs found in the uploaded file to process for {company_name}.',
            'processed_count': 0,
            'error_count': 0
        }), 200


    return jsonify({
        'status': 'success',
        'message': f'Successfully uploaded and processed {processed_count} Q&A pairs for {company_name}.',
        'processed_count': processed_count,
        'error_count': 0
    }), 201 # 201 Created
