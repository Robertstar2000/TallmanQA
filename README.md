TO START CD to "C:\Users\rober\Desktop\TallmanChat-admin-user-qa-management" THEN  TYPE "python run.py"

# TallmanChat

## Project Overview

TallmanChat is a Python-based web application designed as an intelligent Question & Answer (Q&A) tool. It leverages Large Language Models (LLMs) through the OpenAI API to provide answers based on company-specific knowledge bases. The application uses ChromaDB for efficient semantic search and retrieval of relevant context from these knowledge bases, ensuring that the LLM's responses are grounded in factual company data.

Key Features:
- **User Authentication:** Secure login and logout functionality.
- **Role-Based Access:** Differentiates between regular users and administrators, with specific functionalities available to admins (e.g., answer correction, user management).
- **Company-Specific Q&A:** Allows users to select a company (Tallman, MCR, Bradley) to query against its dedicated knowledge base.
- **LLM-Powered Answers:** Utilizes OpenAI's GPT models to generate human-like answers.
- **Contextual Retrieval:** Employs ChromaDB and sentence transformers to find the most relevant text snippets from the selected company's data to inform the LLM.
- **Answer Correction:** Administrators can review and correct answers provided by the LLM, helping to refine the knowledge base over time.
- **User Management:** Administrators can manage user accounts (functionality planned/partially implemented).
- **Persistent Data Storage:** User data is stored in `User.json`, Q&A knowledge is stored in text files (`*_QA.txt`), and ChromaDB uses a persistent local database.

## File Structure

The project is organized as follows:

```
.
├── app/                        # Main application package
│   ├── __init__.py             # Initializes the Flask app and other components
│   ├── app.py                  # Main Flask application runner (entry point for development server)
│   ├── models.py               # Defines data models (User, QA)
│   ├── routes.py               # Defines URL routes and view functions
│   ├── utils.py                # Contains utility functions (data loading, ChromaDB interaction, LLM calls)
│   ├── data/                   # Data storage directory
│   │   ├── Bradley_QA.txt      # Knowledge base for Bradley
│   │   ├── MCR_QA.txt          # Knowledge base for MCR
│   │   ├── Tallman_QA.txt      # Knowledge base for Tallman
│   │   ├── User.json           # Stores user credentials and information
│   │   └── chroma_db/          # Persistent storage for ChromaDB
│   ├── static/                 # Static files (CSS, JavaScript, images) - currently contains .gitkeep
│   └── templates/              # HTML templates for rendering web pages
│       ├── base.html           # Base template for common layout
│       ├── login.html          # Login page
│       ├── screen1.html        # Main Q&A interface page
│       ├── screen2.html        # Answer correction page
│       └── screen3.html        # User management page
├── requirements.txt            # Lists Python package dependencies
├── README.md                   # This file: project documentation
└── tests/                      # Directory for test suite (to be created)
```

## Core Functionalities

### 1. User Authentication
- Users can register (implicitly, via `User.json` initially) and log in using their email and password.
- Session management keeps users logged in across requests.
- Access to certain pages and APIs is restricted based on login status and user role (admin/user).

### 2. Q&A Interaction
- Logged-in users can select a company and a question type.
- They can submit a question to the system.
- The system queries ChromaDB for relevant snippets from the selected company's knowledge base.
- These snippets, along with the user's question, are sent to an OpenAI LLM to generate an answer.
- The answer and retrieved snippets are displayed to the user.

### 3. Answer Correction (Admin)
- Administrators have access to a page where they can view a previously generated answer.
- They can provide corrective feedback or a completely new answer.
- This corrected Q&A pair is then used to update the knowledge base (both the text file and ChromaDB), improving future responses.

### 4. User Management (Admin)
- Administrators can view a list of registered users.
- Further functionalities like adding, editing, or deleting users are planned/partially implemented via API endpoints.

### 5. Knowledge Base Management
- Company-specific Q&A data is stored in simple text files.
- `utils.py` contains functions to load this data and populate/query a ChromaDB vector database for efficient semantic search.
- The `load_all_qa_into_chroma()` function in `utils.py` is used to initialize or update the ChromaDB with the content of the text files.

## Key Python Components

### Models (`app/models.py`)
Defines the data structures used within the application.

-   **`User`**: Represents a user of the application.
    *   Attributes:
        *   `id` (str): Unique identifier for the user.
        *   `name` (str): User's full name.
        *   `email` (str): User's email address (used for login).
        *   `status` (str): User's role (e.g., 'admin', 'user').
        *   `hashed_password` (str): Hashed version of the user's password.
    *   Methods:
        *   `set_password(password)`: Hashes and sets the user's password.
        *   `check_password(password)`: Verifies a given password against the stored hash.
        *   `to_dict()`: Returns a dictionary representation of the user (excluding sensitive info like password directly if needed, though current includes hash).
        *   `from_dict(data)`: Creates a User instance from a dictionary.

-   **`QA`**: Represents a question-answer pair.
    *   Attributes:
        *   `id` (str): Unique identifier for the Q&A pair.
        *   `question` (str): The question text.
        *   `answer` (str): The answer text.
        *   `company` (str): The company to which this Q&A pertains.
    *   Methods:
        *   `to_dict()`: Returns a dictionary representation of the Q&A pair.
        *   `from_dict(data)`: Creates a QA instance from a dictionary.

### Key Utility Functions (`app/utils.py`)
Contains helper functions for various operations.

-   **User Data Management:**
    *   `load_users() -> list[User]`: Loads user data from `User.json`.
    *   `save_users(users: list[User])`: Saves a list of User objects to `User.json`.
    *   `hash_password(password: str) -> str`: Hashes a password.
    *   `verify_password(hashed_password: str, password: str) -> bool`: Verifies a password against a hash.

-   **Q&A Data Management (Text Files):**
    *   `get_qa_filepath(company: str) -> str`: Returns the file path for a given company's Q&A data.
    *   `load_qa_data(company: str) -> list[QA]`: Loads Q&A pairs from the specified company's text file.
    *   `append_qa_pair(company: str, question: str, answer: str, is_update: bool = False) -> QA`: Appends a new Q&A pair to the company's text file and adds it to ChromaDB.

-   **ChromaDB Interaction:**
    *   `get_or_create_collection(company_name: str) -> chromadb.Collection`: Retrieves or creates a ChromaDB collection for the given company.
    *   `add_qa_to_collection(collection: chromadb.Collection, qa_item: QA)`: Adds/updates a Q&A item in the specified ChromaDB collection.
    *   `query_collection(collection: chromadb.Collection, query_text: str, n_results: int = 3) -> list[dict]`: Queries the collection for relevant documents based on the query text.
    *   `load_all_qa_into_chroma()`: Loads all Q&A data from text files into their respective ChromaDB collections. This is crucial for initializing the vector database.

-   **OpenAI LLM Interaction:**
    *   `format_snippets_for_llm(snippets: list[dict]) -> str`: Formats retrieved context snippets into a string suitable for the LLM prompt.
    *   `get_llm_answer(user_question: str, company: str, question_type: str, context_snippets: list[dict]) -> str`: Constructs a prompt and calls the OpenAI API to get an answer for a user's question.
    *   `get_corrected_llm_answer(original_question: str, incorrect_answer: str, user_correction_text: str, company: str) -> str`: Constructs a prompt and calls the OpenAI API to generate a refined answer based on user corrections.

### Routes (`app/routes.py`)
Defines the application's URL endpoints and their corresponding logic.

-   **`/`**: Redirects to `/ask` if logged in, otherwise to `/login`.
-   **`/login` (GET, POST)**: Handles user login.
-   **`/logout` (GET)**: Logs out the current user.
-   **`/ask` (GET)**: Displays the main Q&A page (Screen 1).
-   **`/api/ask` (POST)**: API endpoint for submitting a question. It processes the question, queries ChromaDB, gets an answer from the LLM, and returns the response as JSON.
-   **`/correct_answer_page` (GET)**: Displays the page for correcting an answer (Screen 2), typically for admins.
-   **`/api/correct_answer` (POST)**: API endpoint for submitting a corrected answer. Updates the knowledge base (text file and ChromaDB). Restricted to admins.
-   **`/manage_users` (GET)**: Displays the user management page (Screen 3). Restricted to admins.
-   **`/api/users` (POST)**: API endpoint for adding a new user (admin only, currently a placeholder).
-   **`/api/users/<user_id>` (PUT, DELETE)**: API endpoints for editing or deleting a user (admin only, currently placeholders).

**Decorators:**
-   `@login_required`: Ensures a user is logged in to access the route.
-   `@admin_required`: Ensures a user is logged in and has 'admin' status to access the route.

## Data Files

-   **`app/data/User.json`**: Stores an array of user objects in JSON format. Includes user ID, name, email, status (admin/user), and hashed password.
    *Example structure:*
    ```json
    [
        {
            "id": "some_uuid",
            "name": "Admin User",
            "email": "admin@example.com",
            "status": "admin",
            "hashed_password": "scrypt_hash_here"
        }
    ]
    ```

-   **`app/data/<Company>_QA.txt`** (e.g., `Tallman_QA.txt`, `MCR_QA.txt`, `Bradley_QA.txt`):
    These files store the knowledge base for each company as plain text. Each Q&A pair is typically represented by the question on one line and the answer on the next, separated by a blank line. Lines starting with `##Update##` might indicate entries that were a result of a correction process.
    *Example structure:*
    ```
    What is product X?
    Product X is a revolutionary tool for task automation.

    ##Update##
    How to troubleshoot issue Y?
    To troubleshoot issue Y, first restart the device, then check connections.
    ```

-   **`app/data/chroma_db/`**: This directory is used by ChromaDB to persist its database files. It contains SQLite files and other data necessary for ChromaDB's operation. This directory should typically be included in `.gitignore` if it becomes large or contains sensitive embeddings, but for this project, its existence is noted.

## LDAP Authentication

TallmanChat supports user authentication via an external LDAP directory. This allows users to log in with their existing corporate credentials, centralizing user management.

### How It Works

1.  **LDAP First**: When a user attempts to log in, the application first tries to authenticate them against the configured LDAP server.
2.  **Local Fallback**: If LDAP authentication fails (e.g., the server is unreachable, or the user's credentials are not found in LDAP), the system automatically falls back to the local user database (`User.json`). This ensures that local administrators can always access the application, even if the LDAP service is unavailable.
3.  **Automatic User Creation**: If a user authenticates successfully via LDAP but does not have a profile in the local `User.json` file, a new local profile is created for them automatically. This user is assigned a default 'user' role. An administrator can then elevate their privileges if needed.

### Configuration

LDAP settings are managed by an administrator on the **Admin -> Settings** page (`/manage_users`).

The following settings can be configured:

*   **Enable LDAP**: A toggle to turn LDAP authentication on or off globally.
*   **LDAP Server**: The hostname or IP address of the LDAP server (e.g., `ldap.example.com`).
*   **Port**: The port number for the LDAP service (typically `389` or `636` for SSL).
*   **Use SSL**: A checkbox to enable a secure connection (LDAPS).
*   **Base DN**: The base distinguished name for user searches (e.g., `ou=users,dc=example,dc=com`).
*   **Bind User DN**: The distinguished name of a service account used to connect to and search the LDAP directory (e.g., `cn=admin,dc=example,dc=com`).
*   **Bind User Password**: The password for the service account.

Changes to these settings are saved to `app/data/config.json` and are applied immediately.

## Local LLM Setup with Ollama

TallmanChat can use Ollama to run local LLMs instead of OpenAI's API. This is especially useful for privacy, cost savings, or when internet access is limited.

### Installing Ollama

1. **Download and Install Ollama**
   - Windows: Download the installer from [Ollama's GitHub releases](https://github.com/ollama/ollama/releases)
   - macOS: `brew install ollama`
   - Linux: `curl -fsSL https://ollama.com/install.sh | sh`

2. **Start the Ollama Service**
   - Windows: The installer should start the service automatically
   - macOS/Linux: Run `ollama serve` in a terminal

3. **Download a Model**
   ```bash
   # Example: Download the mistral model (7B parameters)
   ollama pull mistral
   
   # For better performance, you might want to try larger models like:
   # ollama pull llama2
   # ollama pull codellama
   ```

### Configuring TallmanChat to Use Ollama

1. **Install Required Package**
   ```bash
   pip install ollama
   ```

2. **Modify `app/utils.py`**
   Replace the `get_llm_answer` function with the following implementation:

   ```python
   import ollama
   
   def get_llm_answer(user_question: str, company: str, question_type: str, context_snippets: list[dict]) -> str:
       if not context_snippets:
           return "No relevant information found in the knowledge base."
   
       formatted_snippets = format_snippets_for_llm(context_snippets)
       
       try:
           response = ollama.chat(
               model="mistral",  # or your preferred model
               messages=[
                   {"role": "system", "content": f"You are a helpful assistant for {company}. Answer the question based on the provided context."},
                   {"role": "user", "content": f"Question: {user_question}\n\nContext:\n{formatted_snippets}"}
               ]
           )
           return response['message']['content'].strip()
       except Exception as e:
           print(f"Error calling Ollama: {e}")
           # Fall back to the best matching snippet
           if context_snippets and len(context_snippets) > 0:
               return f"Here's the best matching information (LLM unavailable):\n\n{context_snippets[0].get('document', 'No matching content found.')}"
           return "Error generating answer. Please try again later."
   ```

3. **Update `get_corrected_llm_answer`**
   Similarly, update the correction function:

   ```python
   def get_corrected_llm_answer(original_question: str, incorrect_answer: str, user_correction_text: str, company: str) -> str:
       try:
           response = ollama.chat(
               model="mistral",  # or your preferred model
               messages=[
                   {"role": "system", "content": f"You are a helpful assistant for {company}. A user is correcting an answer you provided."},
                   {"role": "user", "content": f"Original question: {original_question}\n\nOriginal answer: {incorrect_answer}\n\nUser's correction: {user_correction_text}\n\nPlease provide an improved answer based on the user's correction."}
               ]
           )
           return response['message']['content'].strip()
       except Exception as e:
           print(f"Error in get_corrected_llm_answer: {e}")
           return "Using your correction directly: " + user_correction_text
   ```

4. **Remove OpenAI Dependency**
   You can now remove the OpenAI package if not needed for other parts of your application:
   ```bash
   pip uninstall openai
   ```

### Performance Considerations

- **Hardware Requirements**: Local LLMs require significant RAM and compute power. The 7B parameter models need at least 8GB of RAM, while larger models need 16GB+.
- **Response Time**: Expect slower responses compared to cloud-based APIs, especially on CPU-only systems.
- **Model Selection**: Start with smaller models (like mistral-7b) and only move to larger models if needed for better quality.
- **GPU Acceleration**: For better performance, ensure you have CUDA-compatible GPU and proper drivers installed.

## Installation and Setup

Follow these steps to set up and run TallmanChat locally:

1.  **Prerequisites:**
    *   Python 3.7+
    *   `pip` (Python package installer)
    *   Git

2.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd TallmanChat
    ```
    (Replace `<repository_url>` with the actual URL of your Git repository)

3.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

4.  **Install Dependencies:**
    Ensure the `requirements.txt` file created in a previous step is present in the root directory.
    ```bash
    pip install -r requirements.txt
    ```

5.  **Set Up Environment Variables:**
    The application requires an OpenAI API key to function. Create a `.env` file in the root directory of the project (ensure this file is listed in your `.gitignore` to prevent committing secrets).
    Add your OpenAI API key to the `.env` file:
    ```
    OPENAI_API_KEY=''
    ```
    The application (`app/utils.py`) will load this key using `os.getenv("OPENAI_API_KEY")`. (Note: The current code directly uses `os.getenv`. For `.env` file loading, a library like `python-dotenv` would be used, which is included in `requirements.txt`. The app should be updated or it should be noted that the environment variable must be set in the system globally if `python-dotenv` is not used to explicitly load the `.env` file.)

6.  **Initialize User Data (if `User.json` is empty or not present):**
    The `app/data/User.json` file stores user credentials. If it's empty or you're setting up for the first time, you'll need to populate it. Here's an example for an admin user. You can manually create/edit this file:
    ```json
    [
        {
            "id": "generated_uuid_1", // Replace with a real UUID
            "name": "Admin User",
            "email": "admin@example.com",
            "status": "admin",
            "hashed_password": "pbkdf2:sha256:generated_hash" // See step 6a
        },
        {
            "id": "generated_uuid_2", // Replace with a real UUID
            "name": "Test User",
            "email": "user@example.com",
            "status": "user",
            "hashed_password": "pbkdf2:sha256:generated_hash_2" // See step 6a
        }
    ]
    ```
    *   **6a. Hashing Passwords:** To generate the `hashed_password`, you can use the following Python script (run this in an environment where Flask and Werkzeug are installed):
        ```python
        from werkzeug.security import generate_password_hash
        # For admin user
        admin_password = 'adminpassword' # Choose a strong password
        hashed_admin_password = generate_password_hash(admin_password)
        print(f"Admin Hashed Password: {hashed_admin_password}")

        # For regular user
        user_password = 'userpassword' # Choose a strong password
        hashed_user_password = generate_password_hash(user_password)
        print(f"User Hashed Password: {hashed_user_password}")
        ```
        Copy the output hash (e.g., `pbkdf2:sha256:...`) into your `User.json` file. Remember to also generate unique IDs (e.g., using `uuid.uuid4().hex` in Python).

7.  **Prepare Q&A Data:**
    Ensure your `app/data/Bradley_QA.txt`, `app/data/MCR_QA.txt`, and `app/data/Tallman_QA.txt` files are populated with your desired question-answer pairs, following the format described in the "Data Files" section.

8.  **Initialize ChromaDB:**
    The first time you run the application, or whenever the source Q&A text files are updated, you need to load the data into ChromaDB. You can do this by running a Python script that calls the `load_all_qa_into_chroma()` function from `app.utils`.
    Create a temporary script in the root directory, e.g., `init_db.py`:
    ```python
    # init_db.py
    import os
    from app.utils import load_all_qa_into_chroma
    from app import create_app # Assuming create_app initializes sentence_transformer_ef if needed globally or by utils

    # If OPENAI_API_KEY is needed for sentence_transformer_ef indirectly, ensure it's set.
    # However, sentence_transformer_ef is typically local.
    # Make sure this script is run from the project root.

    # A simple way to ensure app context if sentence_transformer_ef is app-dependent
    # For this project, utils.py initializes sentence_transformer_ef globally.
    # So, direct call should be fine if dependencies are met.

    if __name__ == '__main__':
        # Check if OPENAI_API_KEY is set, as utils.py prints a warning
        if not os.getenv("OPENAI_API_KEY"):
            print("Warning: OPENAI_API_KEY is not set. This might affect LLM functionalities but usually not local embedding model initialization.")
        print("Initializing ChromaDB...")
        load_all_qa_into_chroma()
        print("ChromaDB initialization complete (or attempted).")

    ```
    Run this script from your terminal (with the virtual environment activated):
    ```bash
    python init_db.py
    ```
    This will populate the `app/data/chroma_db` directory.

9.  **Run the Application:**
    ```powershell
    python run.py
    ```
    The application should now be running (by default, on `http://0.0.0.0:5000` or `http://127.0.0.1:5000`).

## How to Use
Run from the root directory:
```powershell
python run.py
```

1.  **Access the Application:** Open your web browser and navigate to `http://127.0.0.1:5000`.
2.  **Login:** You will be redirected to the login page. Use the credentials you set up in `User.json` (e.g., `admin@example.com` and the password you chose).
3.  **Ask a Question (Screen 1):**
    *   Once logged in, you'll be on the "Ask AI" screen.
    *   Select the `Company` (Tallman, MCR, Bradley) you want to query.
    *   Select the `Question Type` (Product, Sales, etc.).
    *   Type your question in the "Enter your question" field.
    *   Click "Ask AI".
    *   The AI's answer and the snippets used for context will be displayed.
4.  **Correct an Answer (Admin Only - Screen 2):**
    *   If an answer is unsatisfactory, an admin user can choose to correct it. The UI should provide a way to navigate to the correction screen (Screen 2), potentially passing the context of the question and incorrect answer.
    *   On Screen 2, the admin can input the `Original Question`, the `Incorrect Answer` (pre-filled ideally), and their `Correction Text`.
    *   Submitting the correction will update the system's knowledge base.
5.  **Manage Users (Admin Only - Screen 3):**
    *   Admin users can navigate to the "Manage Users" screen.
    *   This screen displays a list of current users.
    *   Functionality to add, edit, or delete users is accessible via API endpoints (`/api/users/...`) but might require frontend implementation or direct API calls for full use.

## Running Tests

This project uses a combination of `unittest` style tests that can be run with a test runner like `pytest`.

1.  **Install Pytest (if not already installed):**
    If you don't have `pytest` installed in your virtual environment:
    ```bash
    pip install pytest
    ```
    (Consider adding `pytest` to `requirements.txt` if it's the recommended way to run tests).

2.  **Navigate to the Root Directory:**
    Ensure you are in the root directory of the project (the `TallmanChat` directory where `tests/` and `app/` are located).

3.  **Run Tests:**
    Execute the following command in your terminal:
    ```bash
    pytest
    ```
    Pytest will automatically discover and run the tests in the `tests/` directory. You should see output indicating the number of tests passed, failed, or skipped.

    If you prefer to use `unittest`'s built-in test discovery:
    ```bash
    python -m unittest discover -s tests -p "test_*.py"
    ```

*(Optional: Add `pytest` to `requirements.txt`)*
If you want to ensure `pytest` is part of the project's standard dependencies, add `pytest` (possibly with a version, e.g., `pytest>=7.0`) to your `requirements.txt` file and have users install it via `pip install -r requirements.txt`.

---
*This README provides a comprehensive guide to understanding, installing, and using TallmanChat.*
