import json
import os
import uuid
import chromadb
from chromadb.utils import embedding_functions

import openai
import requests
import json # For Ollama streaming response
from flask import current_app # To access app.config # Added for LLM integration
import traceback # Add for detailed error logging
import json

import openai # Added for LLM integration

from werkzeug.security import generate_password_hash, check_password_hash

from app.models import User, QA
from app.data.Type import PROMPT_TEMPLATES # Added for LLM integration

# OpenAI API Key Setup
openai.api_key = os.getenv("OPENAI_API_KEY")
if openai.api_key is None:
    print("Warning: OPENAI_API_KEY environment variable not set. LLM functions will not work.")


# Build paths that work from both app directory and root directory
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_ROOT, 'app', 'data')
os.makedirs(DATA_DIR, exist_ok=True) # Ensure the base data directory exists

USER_FILE = os.path.join(DATA_DIR, 'User.json')
TALLMAN_QA_FILE = os.path.join(DATA_DIR, 'Tallman_QA.txt')
MCR_QA_FILE = os.path.join(DATA_DIR, 'MCR_QA.txt')
BRADLEY_QA_FILE = os.path.join(DATA_DIR, 'Bradley_QA.txt')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')

# --- App Configuration Helpers ---

def load_config():
    """Loads the application configuration from config.json."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return default config if file is missing or corrupt
        return {
            "llm_provider": "openai",
            "ollama_endpoint": "http://localhost:11434/api/generate",
            "selected_model": "llama3",
            "ldap": {
                "enabled": False,
                "server": "ldap://your-ldap-server.com",
                "port": 389,
                "use_ssl": False,
                "base_dn": "ou=users,dc=example,dc=com",
                "user_dn": "ou=users",
                "group_dn": "ou=groups",
                "bind_user_dn": "cn=admin,dc=example,dc=com",
                "bind_user_password": "",
                "user_rdn_attr": "cn",
                "user_login_attr": "uid",
                "user_object_filter": "(objectClass=inetOrgPerson)",
                "group_object_filter": "(objectClass=groupOfNames)",
                "group_member_attr": "member"
            }
        }

def save_config(config):
    """Saves the application configuration to config.json."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

CHROMA_DATA_PATH = os.path.join(DATA_DIR, 'chroma_db')
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2" # "all-mpnet-base-v2" is another good one

# Create an Embedding Manager class that ensures consistent initialization and access
class EmbeddingManager:
    _instance = None
    _embedding_function = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the EmbeddingManager"""
        if cls._instance is None:
            cls._instance = EmbeddingManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the EmbeddingManager - but don't create the function yet"""
        # Only create one instance
        if EmbeddingManager._instance is not None:
            raise RuntimeError("This class is a singleton! Use get_instance() instead")
    
    def get_embedding_function(self):
        """Get or create the embedding function"""
        if self._embedding_function is None:
            try:
                print("[INFO] Creating SentenceTransformerEmbeddingFunction...")
                self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=DEFAULT_EMBEDDING_MODEL
                )
                print("[SUCCESS] SentenceTransformerEmbeddingFunction initialized successfully.")
            except Exception as e:
                print(f"[ERROR] Failed to initialize embedding function: {e}")
                raise RuntimeError(f"Failed to initialize embedding function: {e}") 
        return self._embedding_function

# Try to initialize on module load - this makes sure any import errors are caught early
try:
    # Just check that we can import the necessary components, don't create instance yet
    from sentence_transformers import SentenceTransformer
    print("[INFO] sentence-transformers package available. Will initialize when needed.")
except ImportError as e:
    print(f"[FATAL] sentence-transformers package not available: {e}")
    print("[FATAL] Please install with: pip install sentence-transformers")
    raise
=======
USER_FILE = 'app/data/User.json'
TALLMAN_QA_FILE = 'app/data/Tallman_QA.txt'
MCR_QA_FILE = 'app/data/MCR_QA.txt'
BRADLEY_QA_FILE = 'app/data/Bradley_QA.txt'

CHROMA_DATA_PATH = "app/data/chroma_db"
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2" # "all-mpnet-base-v2" is another good one

try:
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=DEFAULT_EMBEDDING_MODEL)
except Exception as e:
    print(f"Error initializing SentenceTransformerEmbeddingFunction: {e}")
    print("ChromaDB embedding functions might not work. Ensure sentence-transformers is installed and model is accessible.")
    sentence_transformer_ef = None # Fallback or handle error appropriately



def hash_password(password: str) -> str:
    return generate_password_hash(password)

def verify_password(hashed_password: str, password: str) -> bool:
    return check_password_hash(hashed_password, password)

def load_users() -> list[User]:
    try:
        with open(USER_FILE, 'r') as f:

            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)

            if f.tell() == 0:
                return []
            data = json.load(f)

            if not data:
                return []
    except FileNotFoundError:
        return []

    except json.JSONDecodeError as e:
        print(f"Error parsing {USER_FILE}: {e}")
        return []

    users = []
    if isinstance(data, list):
        user_data_list = data
    elif isinstance(data, dict):
        user_data_list = [data]


    users = []
    if isinstance(data, dict) and data:
        if data:
            user_data_list = [data]
        else:
            return []
    elif isinstance(data, list):
        user_data_list = data

    else:
        return []

    for user_data in user_data_list:

        if user_data:  # Only process non-empty user data
            try:
                users.append(User.from_dict(user_data))
            except Exception as e:
                print(f"Error creating user from data {user_data}: {e}")
    

        if user_data:
            users.append(User.from_dict(user_data))

    return users

def save_users(users: list[User]) -> None:
    with open(USER_FILE, 'w') as f:
        json.dump([user.to_dict() for user in users], f, indent=4)

def get_qa_filepath(company: str) -> str:
    if company == "Tallman":
        return TALLMAN_QA_FILE
    elif company == "MCR":
        return MCR_QA_FILE
    elif company == "Bradley":
        return BRADLEY_QA_FILE
    else:
        raise ValueError(f"Invalid company name: {company}")

def load_qa_data(company: str) -> list[QA]:
    filepath = get_qa_filepath(company)
    qa_list = []
    try:
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]

            i = 0
            while i < len(lines):
                if lines[i].startswith("##Update##"):
                    i += 1
                    continue

                if i + 1 < len(lines):
                    question = lines[i]
                    answer = lines[i+1]

                    if answer.startswith("##Update##"):
                        i += 1
                        continue

                    qa_id = uuid.uuid4().hex
                    qa_list.append(QA(
                        id=qa_id,
                        question=question,
                        answer=answer,
                        company=company
                    ))
                    i += 2
                else:
                    break
            return qa_list
    except FileNotFoundError:
        return []

def append_qa_pair(company: str, question: str, answer: str, is_update: bool = False) -> QA:
    filepath = get_qa_filepath(company)
    qa_id = uuid.uuid4().hex
    new_qa = QA(id=qa_id, question=question, answer=answer, company=company)

    with open(filepath, 'a') as f:
        if is_update:
            f.write("##Update##\n")
        f.write(f"{question}\n")
        f.write(f"{answer}\n\n")


    try:
        collection = get_or_create_collection(company)
        add_qa_to_collection(collection, new_qa)
        print(f"Appended Q&A for {company} to file and ChromaDB.")
    except Exception as e:
        print(f"Error adding appended Q&A to ChromaDB for {company}: {e}")
        print(f"Will continue without adding to ChromaDB. Data was still written to file.")

    if sentence_transformer_ef is not None:
        try:
            collection = get_or_create_collection(company)
            add_qa_to_collection(collection, new_qa)
            print(f"Appended Q&A for {company} to file and ChromaDB.")
        except Exception as e:
            print(f"Error adding appended Q&A to ChromaDB for {company}: {e}")
    else:
        print("ChromaDB embedding function not available. Skipping add to collection for appended Q&A.")


    return new_qa

def get_or_create_collection(company_name: str) -> chromadb.api.models.Collection.Collection:

    # Get embedding function using the EmbeddingManager
    try:
        # Get the embedding manager instance
        embedding_manager = EmbeddingManager.get_instance()
        # Get the embedding function from the manager
        embedding_function = embedding_manager.get_embedding_function()
        
        collection_name = f"{company_name.lower()}_qa"
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function

    if sentence_transformer_ef is None:
        raise RuntimeError("SentenceTransformerEmbeddingFunction not initialized. Cannot get or create collection.")
    collection_name = f"{company_name.lower()}_qa"
    try:
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=sentence_transformer_ef

        )
        return collection
    except Exception as e:
        print(f"Error getting or creating collection {collection_name}: {e}")
        raise

def add_qa_to_collection(collection: chromadb.api.models.Collection.Collection, qa_item: QA) -> None:
    if not qa_item.id:
        print(f"Warning: QA item for question '{qa_item.question}' is missing an ID. Generating one.")
        qa_item.id = uuid.uuid4().hex

    try:
        collection.upsert(
            ids=[qa_item.id],
            documents=[qa_item.question],
            metadatas=[qa_item.to_dict()]
        )
    except Exception as e:
        print(f"Error upserting QA item {qa_item.id} into collection {collection.name}: {e}")



def query_collection(collection: chromadb.api.models.Collection.Collection, query_text: str, n_results: int = 3) -> list[dict]:
    """
    Queries the ChromaDB collection for relevant documents.

    Args:
        collection: The ChromaDB collection object.
        query_text: The user's question.
        n_results: The number of results to return.

    Returns:
        A list of dictionaries, where each dictionary is a retrieved snippet
        (from the metadata). Returns an empty list on error or if no results.
    """
    try:
        # Ensure n_results does not exceed the number of items in the collection
        count = collection.count()
        if n_results > count:
            n_results = count
        
        # If collection is empty, no need to query
        if count == 0:
            print(f"[DEBUG] Collection {collection.name} is empty. Returning no results.")
            return []


def query_collection(collection: chromadb.api.models.Collection.Collection, query_text: str, n_results: int = 3) -> list[dict]:
    try:

        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

        
        # The 'metadatas' key contains a list of lists of our stored metadata dictionaries.
        # We want the first (and only) list inside.
        if results and results.get('metadatas'):
            print(f"[DEBUG] Found {len(results['metadatas'][0])} results in ChromaDB for query.")
            return results['metadatas'][0]
        else:
            print(f"[DEBUG] No results found in ChromaDB for query.")
            return []
            
    except Exception as e:
        print(f"Error querying collection {collection.name}: {e}")
        return [] # Return an empty list on error

def load_all_qa_into_chroma():
    # No need to check for embedding function here - get_or_create_collection will handle it
    # and raise an appropriate error if it fails
    
    companies = ["Tallman", "MCR", "Bradley"]
    print("Starting to load all Q&A data into ChromaDB...")
    for company in companies:
        print(f"--- Processing company: {company} ---") # Restoring more verbose company processing log
        try:
            print(f"[{company}] Calling load_qa_data...") # Restoring verbose log
            qa_data = load_qa_data(company)
            print(f"[{company}] load_qa_data returned. Found {len(qa_data) if qa_data else 0} items.") # Restoring verbose log

            if not qa_data:
                print(f"[{company}] No Q&A data found. Skipping.") # Restoring verbose log
                continue

            print(f"[{company}] Calling get_or_create_collection...") # Restoring verbose log
            collection = get_or_create_collection(company)
            print(f"[{company}] Successfully got/created collection: {collection.name}") # Restoring verbose log


        if results and results.get('metadatas') and results['metadatas'][0]:
            return results['metadatas'][0]
        return []
    except Exception as e:
        print(f"Error querying collection {collection.name} with text '{query_text}': {e}")
        return []

def load_all_qa_into_chroma():
    if sentence_transformer_ef is None:
        print("SentenceTransformerEmbeddingFunction not initialized. Cannot load Q&A into ChromaDB.")
        return

    companies = ["Tallman", "MCR", "Bradley"]
    print("Starting to load all Q&A data into ChromaDB...")
    for company in companies:
        print(f"Processing company: {company}")
        try:
            qa_data = load_qa_data(company)
            if not qa_data:
                print(f"No Q&A data found for {company}. Skipping.")
                continue

            collection = get_or_create_collection(company)

            ids_batch = []
            documents_batch = []
            metadatas_batch = []


            print(f"[{company}] Preparing batches for {len(qa_data)} Q&A items...") # Restoring verbose log
            for i, qa_item in enumerate(qa_data):
                if not qa_item.id:
                    qa_item.id = uuid.uuid4().hex 
                ids_batch.append(qa_item.id)
                documents_batch.append(qa_item.question) 
                metadatas_batch.append(qa_item.to_dict())
            print(f"[{company}] Batch preparation complete. {len(ids_batch)} items in batch.") # Restoring verbose log

            if ids_batch:
                batch_size = 100  # Define a smaller batch size
                num_batches = (len(ids_batch) + batch_size - 1) // batch_size
                print(f"[{company}] Upserting {len(ids_batch)} items in {num_batches} batches of size {batch_size} into ChromaDB collection '{collection.name}'...")
                
                for i in range(num_batches):
                    start_idx = i * batch_size
                    end_idx = min((i + 1) * batch_size, len(ids_batch))
                    
                    current_ids_batch = ids_batch[start_idx:end_idx]
                    current_documents_batch = documents_batch[start_idx:end_idx]
                    current_metadatas_batch = metadatas_batch[start_idx:end_idx]
                    
                    if not current_ids_batch: # Should not happen if num_batches is correct
                        continue

                    print(f"[{company}] Upserting batch {i+1}/{num_batches} ({len(current_ids_batch)} items)... From index {start_idx} to {end_idx-1}")
                    try:
                        collection.upsert(
                            ids=current_ids_batch,
                            documents=current_documents_batch,
                            metadatas=current_metadatas_batch
                        )
                        print(f"[{company}] Successfully upserted batch {i+1}/{num_batches}.", flush=True)
                    except Exception as batch_exc:
                        print(f"[{company}] ERROR upserting batch {i+1}/{num_batches}: {batch_exc}", flush=True)
                        traceback.print_exc() # Print full traceback for this specific batch error
                        # Decide if you want to break the loop or continue with next batch
                        # For now, let's break to see the first error clearly.
                        print(f"[{company}] Aborting further batch upserts for this company due to error.", flush=True)
                        break # Exit the batch loop for this company
                print(f"[{company}] Successfully upserted all {len(ids_batch)} items into ChromaDB.")
            else:
                print(f"[{company}] No items to upsert.") # Restoring verbose log

        except ValueError as ve:
            print(f"[{company}] Configuration error during data loading: {ve}", flush=True)
            traceback.print_exc()
        except Exception as e:
            print(f"[{company}] An unexpected error occurred while loading Q&A data into ChromaDB for {company}: {e}", flush=True)
            traceback.print_exc()

            for qa_item in qa_data:
                if not qa_item.id:
                    qa_item.id = uuid.uuid4().hex
                ids_batch.append(qa_item.id)
                documents_batch.append(qa_item.question)
                metadatas_batch.append(qa_item.to_dict())

            if ids_batch:
                collection.upsert(ids=ids_batch, documents=documents_batch, metadatas=metadatas_batch)
                print(f"Successfully loaded {len(ids_batch)} Q&A items into ChromaDB for {company}.")
            else:
                print(f"No new Q&A items to load for {company} after processing.")

        except ValueError as ve:
            print(f"Configuration error for {company}: {ve}")
        except Exception as e:
            print(f"An error occurred while loading Q&A data for {company} into ChromaDB: {e}")


    print("Finished loading all Q&A data into ChromaDB.")

# LLM Integration Functions
def format_snippets_for_llm(snippets: list[dict]) -> str:
    if not snippets:
        return "No relevant information found."

    formatted_string = ""
    for i, snippet_dict in enumerate(snippets):
        # snippet_dict is a QA object in dict form, from ChromaDB metadata
        question = snippet_dict.get('question', 'N/A')
        answer = snippet_dict.get('answer', 'N/A')
        formatted_string += f"Snippet {i+1}: Q: {question} A: {answer}\n"
    return formatted_string.strip()


def get_llm_answer(user_question: str, company: str, question_type: str, context_snippets: list[dict], llm_provider: str, ollama_endpoint: str = None, selected_model: str = None) -> str:
    print(f"[LLM_DEBUG] get_llm_answer called with question: '{user_question[:50]}...', company: {company}, type: {question_type}, provider: {llm_provider}", flush=True)

    if not context_snippets:
        print("[LLM_INFO] No context snippets provided. Skipping LLM call.", flush=True)
        return "LLM_SKIPPED_NO_CONTEXT"

    template = PROMPT_TEMPLATES.get(question_type, PROMPT_TEMPLATES["Default"])
    formatted_snippets_for_prompt = format_snippets_for_llm(context_snippets)
    final_prompt = template.format(user_question=user_question, context_snippets=formatted_snippets_for_prompt)
    print(f"[LLM_DEBUG] Final prompt for LLM (first 100 chars): {final_prompt[:100]}...", flush=True)

    if llm_provider == 'openai':
        if not openai.api_key:
            print("[LLM_INFO] OpenAI API key not configured. Skipping LLM call.", flush=True)
            return "LLM_SERVICE_NOT_CONFIGURED"
        model = selected_model or 'gpt-3.5-turbo'
        try:
            print(f"[LLM_DEBUG] Attempting OpenAI API call with model {model}", flush=True)
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"You are a helpful assistant for the {company} company."},
                    {"role": "user", "content": final_prompt}
                ],
                request_timeout=20
            )
            llm_response_content = response.choices[0].message.content.strip()
            print(f"[LLM_DEBUG] OpenAI API call successful. Response (first 100 chars): {llm_response_content[:100]}...", flush=True)
            return llm_response_content
        except openai.error.AuthenticationError as auth_err:
            print(f"[LLM_ERROR] OpenAI API AuthenticationError: {auth_err}", flush=True)
            return "LLM_AUTHENTICATION_ERROR"
        except openai.error.Timeout as timeout_err:
            print(f"[LLM_ERROR] OpenAI API TimeoutError: {timeout_err}", flush=True)
            return "LLM_TIMEOUT_ERROR"
        except openai.error.OpenAIError as api_err:
            print(f"[LLM_ERROR] OpenAI API Error: {api_err}", flush=True)
            return "LLM_API_ERROR"
        except Exception as e:
            print(f"[LLM_ERROR] General error calling OpenAI LLM: {e}", flush=True)
            traceback.print_exc()
            return "LLM_GENERAL_ERROR"

    elif llm_provider == 'ollama':
        endpoint = ollama_endpoint or 'http://localhost:11434/api/generate'
        model = selected_model or 'llama2'
        payload = {
            "model": model,
            "prompt": final_prompt,
            "stream": False,
            "system": f"You are a helpful assistant for the {company} company."
        }
        try:
            print(f"[LLM_DEBUG] Attempting Ollama API call to {endpoint} with model {model}", flush=True)
            response = requests.post(
                endpoint, 
                json=payload, 
                timeout=60
            )
            response.raise_for_status()
            response_data = response.json()
            llm_response_content = response_data.get('response', '').strip()
            print(f"[LLM_DEBUG] Ollama API call successful. Response (first 100 chars): {llm_response_content[:100]}...", flush=True)
            return llm_response_content
        except requests.exceptions.Timeout as timeout_err:
            print(f"[LLM_ERROR] Ollama API TimeoutError: {timeout_err}", flush=True)
            return "LLM_TIMEOUT_ERROR"
        except requests.exceptions.RequestException as req_err:
            print(f"[LLM_ERROR] Ollama API RequestException: {req_err}", flush=True)
            return "LLM_API_ERROR"
        except Exception as e:
            print(f"[LLM_ERROR] General error calling Ollama LLM: {e}", flush=True)
            traceback.print_exc()
            return "LLM_GENERAL_ERROR"
    else:
        print(f"[LLM_ERROR] Unknown LLM provider configured: {llm_provider}", flush=True)
        return "LLM_PROVIDER_NOT_SUPPORTED"

def get_corrected_llm_answer(original_question: str, incorrect_answer: str, user_correction_text: str, company: str) -> str:
    if not openai.api_key or not openai.api_key.strip():
        return "LLM correction not available. Using your correction directly: " + user_correction_text
=======
def get_llm_answer(user_question: str, company: str, question_type: str, context_snippets: list[dict]) -> str:
    if not openai.api_key:
        return "OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable."

    template = PROMPT_TEMPLATES.get(question_type, PROMPT_TEMPLATES["Default"])
    formatted_snippets = format_snippets_for_llm(context_snippets)

    final_prompt = template.format(user_question=user_question, context_snippets=formatted_snippets)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a helpful assistant for the {company} company."},
                {"role": "user", "content": final_prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Error generating answer from LLM."

def get_corrected_llm_answer(original_question: str, incorrect_answer: str, user_correction_text: str, company: str) -> str:
    if not openai.api_key:
        return "OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable."

    template = PROMPT_TEMPLATES["Correct"]
    final_prompt = template.format(
        user_question=original_question,
        incorrect_answer=incorrect_answer,
        user_correction_text=user_correction_text
    )


    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[

                {"role": "system", "content": f"You are a helpful assistant for the {company} company. A user is correcting an answer you provided."},
                {"role": "user", "content": f"Original question: {original_question}\n\nOriginal answer: {incorrect_answer}\n\nUser's correction: {user_correction_text}\n\nPlease provide an improved answer based on the user's correction."}

                {"role": "system", "content": f"You are a helpful assistant for the {company} company, tasked with correcting a previous answer based on user feedback."},
                {"role": "user", "content": final_prompt}

            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:

        print(f"Error in get_corrected_llm_answer: {e}")
        # Fall back to using the user's correction directly if LLM fails
        return "Using your correction directly: " + user_correction_text

        print(f"Error calling OpenAI API for correction: {e}")
        return "Error generating corrected answer from LLM."


# Note for environment setup:
# Ensure 'chromadb', 'sentence-transformers', and 'openai' are installed.
# pip install chromadb sentence-transformers openai
# Also, set the OPENAI_API_KEY environment variable.
