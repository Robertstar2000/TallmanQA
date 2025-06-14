import unittest
from unittest.mock import patch, MagicMock
from app.utils import (
    format_snippets_for_llm,
    get_llm_answer,
    get_corrected_llm_answer,
    # Make sure openai from utils can be patched
)
# If PROMPT_TEMPLATES is used directly in tests from app.data.Type, import it
from app.data.Type import PROMPT_TEMPLATES

# Patch 'app.utils.openai' to mock the openai module as used in utils.py
@patch('app.utils.openai')
class TestLLMOperations(unittest.TestCase):

    def test_format_snippets_for_llm_empty(self, mock_openai_module): # mock_openai_module is from class decorator
        self.assertEqual(format_snippets_for_llm([]), "No relevant information found.")

    def test_format_snippets_for_llm_single_snippet(self, mock_openai_module):
        snippets = [{'question': 'Q1', 'answer': 'A1'}]
        expected = "Snippet 1: Q: Q1 A: A1"
        self.assertEqual(format_snippets_for_llm(snippets), expected)

    def test_format_snippets_for_llm_multiple_snippets(self, mock_openai_module):
        snippets = [
            {'question': 'Q1', 'answer': 'A1'},
            {'question': 'Q2', 'answer': 'A2'}
        ]
        expected = "Snippet 1: Q: Q1 A: A1\nSnippet 2: Q: Q2 A: A2"
        self.assertEqual(format_snippets_for_llm(snippets), expected)

    def test_get_llm_answer_success(self, mock_openai_module):
        mock_openai_module.api_key = "fake_key" # Ensure API key is seen as "set"
        mock_response = MagicMock()
        mock_response.choices[0].message.content = " Mocked LLM Answer "
        mock_openai_module.ChatCompletion.create.return_value = mock_response

        user_question = "What is AI?"
        company = "TestCo"
        question_type = "Default" # Assumes "Default" is a key in PROMPT_TEMPLATES
        context_snippets = [{'question': 'Context Q', 'answer': 'Context A'}]

        answer = get_llm_answer(user_question, company, question_type, context_snippets)

        self.assertEqual(answer, "Mocked LLM Answer")
        mock_openai_module.ChatCompletion.create.assert_called_once()
        call_args = mock_openai_module.ChatCompletion.create.call_args

        # Check model
        self.assertEqual(call_args.kwargs['model'], "gpt-3.5-turbo")
        # Check messages structure and content (especially the user message)
        messages = call_args.kwargs['messages']
        self.assertEqual(messages[0]['role'], "system")
        self.assertIn(company, messages[0]['content'])
        self.assertEqual(messages[1]['role'], "user")

        # Verify the prompt construction
        expected_formatted_snippets = format_snippets_for_llm(context_snippets)
        expected_prompt = PROMPT_TEMPLATES[question_type].format(
            user_question=user_question,
            context_snippets=expected_formatted_snippets
        )
        self.assertEqual(messages[1]['content'], expected_prompt)


    def test_get_llm_answer_no_api_key(self, mock_openai_module):
        mock_openai_module.api_key = None # Simulate API key not set
        answer = get_llm_answer("Q", "C", "T", [])
        self.assertEqual(answer, "OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable.")
        mock_openai_module.ChatCompletion.create.assert_not_called()

    def test_get_llm_answer_api_error(self, mock_openai_module):
        mock_openai_module.api_key = "fake_key"
        mock_openai_module.ChatCompletion.create.side_effect = Exception("API communication error")

        answer = get_llm_answer("Q", "C", "T", [])
        self.assertEqual(answer, "Error generating answer from LLM.")


    def test_get_corrected_llm_answer_success(self, mock_openai_module):
        mock_openai_module.api_key = "fake_key"
        mock_response = MagicMock()
        mock_response.choices[0].message.content = " Mocked Corrected Answer "
        mock_openai_module.ChatCompletion.create.return_value = mock_response

        original_question = "Original Q"
        incorrect_answer = "Incorrect A"
        user_correction_text = "User correction"
        company = "TestCo"

        corrected_answer = get_corrected_llm_answer(original_question, incorrect_answer, user_correction_text, company)

        self.assertEqual(corrected_answer, "Mocked Corrected Answer")
        mock_openai_module.ChatCompletion.create.assert_called_once()
        call_args = mock_openai_module.ChatCompletion.create.call_args

        self.assertEqual(call_args.kwargs['model'], "gpt-3.5-turbo")
        messages = call_args.kwargs['messages']
        self.assertEqual(messages[0]['role'], "system")
        self.assertIn(company, messages[0]['content'])
        self.assertEqual(messages[1]['role'], "user")

        expected_prompt = PROMPT_TEMPLATES["Correct"].format(
            user_question=original_question,
            incorrect_answer=incorrect_answer,
            user_correction_text=user_correction_text
        )
        self.assertEqual(messages[1]['content'], expected_prompt)

    def test_get_corrected_llm_answer_no_api_key(self, mock_openai_module):
        mock_openai_module.api_key = None
        answer = get_corrected_llm_answer("OQ", "IA", "UC", "C")
        self.assertEqual(answer, "OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable.")
        mock_openai_module.ChatCompletion.create.assert_not_called()

    def test_get_corrected_llm_answer_api_error(self, mock_openai_module):
        mock_openai_module.api_key = "fake_key"
        mock_openai_module.ChatCompletion.create.side_effect = Exception("API communication error")
        answer = get_corrected_llm_answer("OQ", "IA", "UC", "C")
        self.assertEqual(answer, "Error generating corrected answer from LLM.")


if __name__ == '__main__':
    unittest.main()
