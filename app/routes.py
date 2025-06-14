from functools import wraps
from flask import render_template, request, redirect, url_for, jsonify, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import app, ldap_manager, config
from app.models import User, QA
import uuid
from app.utils import (
    get_llm_answer,
    load_qa_data, append_qa_pair, load_config, save_config,
    get_or_create_collection, format_snippets_for_llm, load_users, save_users,
    query_collection
)
import json

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('ask_ai_get'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('ask_ai_get'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return jsonify({'status': 'error', 'message': 'Email and password are required.'}), 400

        user_to_login = None
        auth_method = 'local'

        # Try LDAP first if enabled
        if config.get('ldap', {}).get('enabled', False):
            try:
                response = ldap_manager.authenticate(email, password)
                if response.status.value == 0:  # LDAP_SUCCESS
                    users_list_ldap = load_users()
                    user_to_login = None
                    for u_ldap in users_list_ldap:
                        if u_ldap.email == email:
                            user_to_login = u_ldap
                            break
                    auth_method = 'LDAP'
                    if not user_to_login:
                        return jsonify({'status': 'error', 'message': 'LDAP login successful, but no local user profile found.'}), 403
            except Exception as e:
                print(f"[ERROR] LDAP connection failed: {e}")
                # Fall through to local auth if LDAP server is down
        
        # Fallback to local authentication
        if not user_to_login:
            users_list_for_local_auth = load_users()
            local_user = None
            for user_candidate in users_list_for_local_auth:
                if user_candidate.email == email:
                    local_user = user_candidate
                    break
            if local_user and local_user.check_password(password):
                user_to_login = local_user
                auth_method = 'local'
        
        if user_to_login:
            login_user(user_to_login)
            return jsonify({'status': 'success', 'message': f'{auth_method.capitalize()} login successful!', 'redirect_url': url_for('ask_ai_get')})
        else:
            message = 'Invalid email or password.'
            return jsonify({'status': 'error', 'message': message}), 401

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if not current_user.is_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('ask_ai_get'))
        return f(*args, **kwargs)
    return decorated_function

# Renamed placeholder ask_ai to ask_ai_get for clarity
@app.route('/ask', methods=['GET'])
@login_required
def ask_ai_get():
    return render_template('screen1.html')

@app.route('/api/config', methods=['GET'])
@login_required
def get_config():
    """API endpoint to get the current application configuration."""
    if not current_user.is_admin():
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403
    
    config = load_config()
    # For security, never send the bind password to the client
    if 'ldap' in config and 'bind_user_password' in config['ldap']:
        config['ldap']['bind_user_password'] = ''
        
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
@login_required
def update_config():
    """API endpoint to update the application configuration."""
    if not current_user.is_admin():
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403
    
    new_config_data = request.get_json()
    if not new_config_data:
        return jsonify({'status': 'error', 'message': 'Invalid configuration data'}), 400
    
    try:
        current_config = load_config()
        
        # If the password in the submitted data is empty, it means "don't change it".
        if 'ldap' in new_config_data and 'bind_user_password' in new_config_data.get('ldap', {}):
            if not new_config_data['ldap']['bind_user_password']:
                new_config_data['ldap']['bind_user_password'] = current_config.get('ldap', {}).get('bind_user_password', '')

        # Deep update the current config with new data
        for key, value in new_config_data.items():
            if isinstance(value, dict) and key in current_config and isinstance(current_config[key], dict):
                current_config[key].update(value)
            else:
                current_config[key] = value

        save_config(current_config)
        return jsonify({'status': 'success', 'message': 'Configuration saved successfully'})
    except Exception as e:
        print(f"[ERROR] Could not save config: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to save configuration'}), 500


@app.route('/api/ask', methods=['POST']) # API endpoint for asking questions
@login_required
def ask_ai_post():
    print("[DEBUG] /api/ask route called")
    try:
        # Ensure we have JSON data
        if not request.is_json:
            print("[ERROR] Request is not JSON")
            return jsonify({
                'status': 'error',
                'message': 'Request must be JSON',
                'code': 'invalid_content_type'
            }), 400
            
        data = request.get_json()
        print(f"[DEBUG] Request data: {data}")
        
        if not data:
            print("[ERROR] No data provided in request")
            return jsonify({
                'status': 'error',
                'message': 'No data provided',
                'code': 'no_data'
            }), 400
            
        # Extract and validate required fields
        user_question = data.get('user_question', '').strip()
        company = data.get('company', '').strip()
        question_type = data.get('question_type', '').strip()
        print(f"[DEBUG] Extracted fields: question='{user_question}', company='{company}', type='{question_type}'")


        # Check for missing required fields
        missing_fields = []
        if not user_question:
            missing_fields.append('user_question')
        if not company:
            missing_fields.append('company')
        if not question_type:
            missing_fields.append('question_type')
            
        if missing_fields:
            return jsonify({
                'status': 'error',
                'message': f'Missing required fields: {', '.join(missing_fields)}',
                'code': 'missing_fields',
                'missing_fields': missing_fields
            }), 400

        # Validate company and question_type
        valid_companies = ["Tallman", "MCR", "Bradley"]
        valid_question_types = ["Product", "Sales", "General Help", "Tutorial", "Default"]
        
        if company not in valid_companies:
            return jsonify({
                'status': 'error',
                'message': f'Invalid company: {company}. Must be one of: {', '.join(valid_companies)}',
                'code': 'invalid_company',
                'valid_companies': valid_companies
            }), 400
            
        if question_type not in valid_question_types:
            return jsonify({
                'status': 'error',
                'message': f'Invalid question type: {question_type}. Must be one of: {', '.join(valid_question_types)}',
                'code': 'invalid_question_type',
                'valid_question_types': valid_question_types
            }), 400

        # Initialize ChromaDB collection for the company
        try:
            print(f"[DEBUG] Getting collection for company: {company}")
            collection = get_or_create_collection(company)
            print(f"[DEBUG] Successfully got collection: {collection.name}")
        except Exception as e:
            print(f"[ERROR] Failed to get collection: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Error accessing database: {str(e)}',
                'code': 'database_error'
            }), 500
        
        # Query ChromaDB for relevant snippets
        try:
            print(f"[DEBUG] Querying collection with: {user_question}")
            retrieved_snippets_dicts = query_collection(collection, user_question, n_results=3)
            print(f"[DEBUG] Retrieved {len(retrieved_snippets_dicts)} snippets")
        except Exception as e:
            print(f"[ERROR] Failed to query collection: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Error querying database: {str(e)}',
                'code': 'query_error'
            }), 500
        
        # Get LLM answer (this will use Ollama if configured, otherwise fall back        # Semantic search done, now try LLM
        # Load the latest config for each request (reflects admin UI changes)
        config = load_config()
        llm_provider = config.get('llm_provider', 'openai')
        ollama_endpoint = config.get('ollama_endpoint', 'http://localhost:11434/api/generate')
        selected_model = config.get('selected_model', 'llama2')
        try:
            print(f"[DEBUG] Getting LLM answer using provider: {llm_provider}, endpoint: {ollama_endpoint}, model: {selected_model}")
            llm_answer = get_llm_answer(
                user_question,
                company,
                question_type,
                retrieved_snippets_dicts,
                llm_provider,
                ollama_endpoint,
                selected_model
            )
            print(f"[DEBUG] LLM answer length: {len(llm_answer) if llm_answer else 0}")
        except Exception as e:
            print(f"[ERROR] Failed to get LLM answer: {e}")
            # Continue with fallback mechanism instead of failing
            llm_answer = f"Error generating answer from LLM: {str(e)}"
        
        # Format snippets for display
        try:
            print(f"[DEBUG] Retrieved snippets dicts: {retrieved_snippets_dicts}")
            print(f"[DEBUG] Formatting snippets for display")
            display_snippets = format_snippets_for_llm(retrieved_snippets_dicts)
            print(f"[DEBUG] Display snippets length: {len(display_snippets) if display_snippets else 0}")
        except Exception as e:
            print(f"[ERROR] Failed to format snippets: {e}")
            display_snippets = "Error formatting snippets."

        # Define conditions for LLM failure
        LLM_FAILURE_SIGNALS = [
            "LLM_SERVICE_NOT_CONFIGURED",
            "LLM_SKIPPED_NO_CONTEXT",
            "LLM_AUTHENTICATION_ERROR",
            "LLM_TIMEOUT_ERROR",
            "LLM_API_ERROR",
            "LLM_GENERAL_ERROR",
            "LLM_PROVIDER_NOT_SUPPORTED",
            "Error generating answer from LLM" # Keep old generic one
        ]

        llm_response_is_error_signal = llm_answer in LLM_FAILURE_SIGNALS
        # Check if llm_answer is not None and not an error signal before checking length
        llm_response_too_short = (
            llm_answer is not None and 
            not llm_response_is_error_signal and 
            len(llm_answer) < 100 # Arbitrary short length, e.g., less than 100 characters
        )

        llm_failed = llm_answer is None or llm_response_is_error_signal or llm_response_too_short

        final_answer = llm_answer # Default to LLM answer
        answer_source = "LLM"    # Default to LLM source

        if llm_failed:
            failure_reason_log = {
                'signal': llm_answer if llm_response_is_error_signal else 'N/A', 
                'too_short': llm_response_too_short, 
                'is_none': llm_answer is None
            }
            print(f"[FALLBACK_INFO] LLM attempt failed or response inadequate. Reason: {failure_reason_log}. Proceeding to fallback.", flush=True)
            print(f"[FALLBACK_DEBUG] LLM raw response/signal was: {llm_answer!r}", flush=True)
            
            if retrieved_snippets_dicts:
                first_snippet = retrieved_snippets_dicts[0]
                print(f"[FALLBACK_DEBUG] First snippet for fallback: {first_snippet!r}", flush=True)
                
                ans_content = first_snippet.get('answer', '').strip()
                ques_content = first_snippet.get('question', '').strip()
                
                fallback_answer_text = f"Based on the available information: {ans_content}"
                if ques_content and ques_content.lower() != 'n/a' and ques_content.strip(): # Ensure ques_content is meaningful
                    fallback_answer_text = f"Regarding a question similar to '{ques_content}': {ans_content}"
                
                final_answer = fallback_answer_text
                answer_source = "Semantic Search Fallback"
                print(f"[FALLBACK_DEBUG] Using semantic search fallback. Answer: {final_answer[:100]}...", flush=True)
            else: # LLM failed AND no snippets
                final_answer = "I could not retrieve an answer using the language model, and no relevant information was found in our knowledge base for your query."
                answer_source = "No Information"
                print(f"[FALLBACK_DEBUG] LLM failed and no snippets found.", flush=True)
        else: # LLM was successful
            print(f"[LLM_SUCCESS] LLM answer generated successfully. Using LLM response.", flush=True)

        # Prepare the single, consolidated response
        llm_failed_reason_for_json = 'N/A'
        if llm_response_is_error_signal:
            llm_failed_reason_for_json = llm_answer
        elif llm_response_too_short:
            llm_failed_reason_for_json = 'response_too_short'
        elif llm_answer is None:
            llm_failed_reason_for_json = 'response_is_none'

        return jsonify({
            'status': 'success',
            'answer': final_answer,
            'references': retrieved_snippets_dicts, 'references_formatted': display_snippets, 
            'answer_source': answer_source,
            'llm_response_raw': llm_answer if isinstance(llm_answer, str) else str(llm_answer), # Ensure llm_answer is stringified for JSON
            'llm_failed_reason': llm_failed_reason_for_json
        })

        
    except RuntimeError as r_e:
        # Handle runtime errors (e.g., ChromaDB not initialized)
        app.logger.error(f"Runtime error in /api/ask: {str(r_e)}")
        return jsonify({
            'status': 'error',
            'message': f'Runtime error: {str(r_e)}',
            'code': 'runtime_error'
        }), 500
        
    except Exception as e:
        # Log the traceback for debugging
        print("[ERROR] Exception in ask_ai_post:")
        import traceback
        traceback.print_exc()
        import sys
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_details = traceback.format_exception(exc_type, exc_value, exc_traceback)
        print("[ERROR] Detailed traceback:")
        for line in tb_details:
            print(line.strip())
        
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred while processing your request.',
            'code': 'internal_error'
        }), 500


@app.route('/correct_answer_page', methods=['GET'])
@admin_required
def correct_answer_page_get():
    # Get parameters from the request
    original_question = request.args.get('original_question', '')
    incorrect_answer = request.args.get('incorrect_answer', '')
    company = request.args.get('company', 'Tallman')  # Default to Tallman if not provided
    
    # If we have raw snippets in the URL, try to extract the first one
    raw_snippets = request.args.get('raw_snippets')
    first_snippet = ''
    
    if raw_snippets:
        try:
            snippets = json.loads(raw_snippets)
            if snippets and isinstance(snippets, list) and len(snippets) > 0:
                first_snippet = snippets[0].get('answer', '')
        except (json.JSONDecodeError, AttributeError) as e:
            app.logger.error(f"Error parsing raw_snippets: {e}")
    
    # If we still don't have an answer, use the incorrect_answer or a default message
    answer_to_display = first_snippet or incorrect_answer or 'No answer content available.'
    
    return render_template('screen2.html',
                         original_question=original_question,
                         incorrect_answer=answer_to_display,
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
