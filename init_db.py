# init_db.py
# Script to initialize and populate ChromaDB with Q&A data for all companies.
# Run this after setting up your virtualenv and installing requirements.

import os
from app.utils import load_all_qa_into_chroma

if __name__ == "__main__":
    print("Initializing ChromaDB with Q&A data...")
    load_all_qa_into_chroma()
    print("ChromaDB initialization complete. Data is ready.")
