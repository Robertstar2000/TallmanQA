PROMPT_TEMPLATES = {
    "Product": "Question: {user_question}\nKnown Information: {context_snippets}\nAnswer the question based on the known information about the product.",
    "Sales": "Question: {user_question}\nRelevant Sales Info: {context_snippets}\nProvide a sales-oriented answer to the question using the provided information.",
    "General Help": "Question: {user_question}\nContext: {context_snippets}\nProvide a helpful answer to the user's question using the given context.",
    "Tutorial": "Question: {user_question}\nTutorial Information: {context_snippets}\nExplain how to do this, based on the tutorial information provided.",
    "Correct": "Original Question: {user_question}\nIncorrect Answer: {incorrect_answer}\nUser's Correction/New Information: {user_correction_text}\nPlease generate a new, improved answer based on the user's correction. If the user provides a full new answer, use that. If they provide a partial correction, integrate it smoothly.",
    "Default": "Question: {user_question}\nContext: {context_snippets}\nAnswer the following question based on the provided context."
}
