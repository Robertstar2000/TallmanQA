import json
import os
import uuid
import chromadb
from chromadb.utils import embedding_functions
import openai # Added for LLM integration
from werkzeug.security import generate_password_hash, check_password_hash

from app.models import User, QA
from app.data.Type import PROMPT_TEMPLATES # Added for LLM integration

# OpenAI API Key Setup
openai.api_key = os.getenv("OPENAI_API_KEY")
if openai.api_key is None:
    print("Warning: OPENAI_API_KEY environment variable not set. LLM functions will not work.")

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
            if f.tell() == 0:
                return []
            data = json.load(f)
            if not data:
                return []
    except FileNotFoundError:
        return []

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
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
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
                {"role": "system", "content": f"You are a helpful assistant for the {company} company, tasked with correcting a previous answer based on user feedback."},
                {"role": "user", "content": final_prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI API for correction: {e}")
        return "Error generating corrected answer from LLM."

# Note for environment setup:
# Ensure 'chromadb', 'sentence-transformers', and 'openai' are installed.
# pip install chromadb sentence-transformers openai
# Also, set the OPENAI_API_KEY environment variable.
