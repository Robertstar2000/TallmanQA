import unittest
from unittest.mock import patch, MagicMock, call
from app.utils import (
    get_or_create_collection,
    add_qa_to_collection,
    query_collection,
    load_all_qa_into_chroma,
    # Make sure client and sentence_transformer_ef from utils can be patched
)
from app.models import QA # Required for creating QA instances

# To mock app.utils.client and app.utils.sentence_transformer_ef effectively,
# they must be imported and patched where they are LOOKED UP, not where they are defined.
# So, if a function in app.utils uses app.utils.client, patching 'app.utils.client' is correct.

class TestChromaDBOperations(unittest.TestCase):

    @patch('app.utils.client') # Mocks chromadb.PersistentClient instance in utils
    @patch('app.utils.sentence_transformer_ef') # Mocks the embedding function instance in utils
    def test_get_or_create_collection_success(self, mock_ef, mock_chroma_client):
        mock_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_collection
        mock_ef_instance = mock_ef # sentence_transformer_ef itself is the mock

        company_name = "TestCompany"
        collection = get_or_create_collection(company_name)

        mock_chroma_client.get_or_create_collection.assert_called_once_with(
            name=f"{company_name.lower()}_qa",
            embedding_function=mock_ef_instance
        )
        self.assertEqual(collection, mock_collection)

    @patch('app.utils.sentence_transformer_ef', new=None) # Simulate embedding function not initialized
    def test_get_or_create_collection_no_ef(self):
        with self.assertRaisesRegex(RuntimeError, "SentenceTransformerEmbeddingFunction not initialized"):
            get_or_create_collection("TestCompany")

    def test_add_qa_to_collection(self):
        mock_collection = MagicMock()
        qa_item = QA(id="test_id_1", question="Q1", answer="A1", company="TestCo")

        add_qa_to_collection(mock_collection, qa_item)

        mock_collection.upsert.assert_called_once_with(
            ids=[qa_item.id],
            documents=[qa_item.question],
            metadatas=[qa_item.to_dict()]
        )

    @patch('uuid.uuid4') # To control ID generation if QA item has no ID
    def test_add_qa_to_collection_no_id(self, mock_uuid):
        mock_uuid.return_value.hex = "generated_uuid"
        mock_collection = MagicMock()
        qa_item_no_id = QA(question="Q_no_id", answer="A_no_id", company="TestCo") # ID is None

        add_qa_to_collection(mock_collection, qa_item_no_id)

        # Verify that an ID was generated and used
        self.assertEqual(qa_item_no_id.id, "generated_uuid")
        mock_collection.upsert.assert_called_once_with(
            ids=["generated_uuid"],
            documents=[qa_item_no_id.question],
            metadatas=[qa_item_no_id.to_dict()] # This will now include the generated ID
        )


    def test_query_collection_success(self):
        mock_collection = MagicMock()
        query_text = "search for this"
        n_results = 2
        expected_metadatas = [[{'question': 'Q1', 'answer': 'A1'}]] # Chroma returns list of lists for metadatas
        mock_collection.query.return_value = {
            'ids': [['id1']],
            'documents': [['doc1']],
            'metadatas': expected_metadatas,
            'distances': [[0.1]]
        }

        results = query_collection(mock_collection, query_text, n_results=n_results)

        mock_collection.query.assert_called_once_with(
            query_texts=[query_text],
            n_results=n_results
        )
        self.assertEqual(results, expected_metadatas[0])

    def test_query_collection_no_results(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {'metadatas': [None]} # Simulate no metadata found
        results = query_collection(mock_collection, "query", n_results=1)
        self.assertEqual(results, [])

        mock_collection.query.return_value = {'metadatas': [[]]} # Simulate empty list of metadata
        results = query_collection(mock_collection, "query", n_results=1)
        self.assertEqual(results, [])

    @patch('app.utils.load_qa_data')
    @patch('app.utils.get_or_create_collection')
    @patch('app.utils.sentence_transformer_ef') # Ensure it's mocked and not None
    @patch('app.utils.client') # Ensure client is mocked
    def test_load_all_qa_into_chroma(self, mock_chroma_client, mock_ef, mock_get_create_collection, mock_load_qa):
        # Setup: sentence_transformer_ef is mocked by @patch decorator
        # mock_ef is the MagicMock instance for sentence_transformer_ef

        # Mock data for two companies
        qa_items_company1 = [
            QA(id="c1_q1", question="C1Q1", answer="C1A1", company="Company1"),
            QA(id="c1_q2", question="C1Q2", answer="C1A2", company="Company1")
        ]
        qa_items_company2 = [
            QA(id="c2_q1", question="C2Q1", answer="C2A1", company="Company2")
        ]

        # Configure load_qa_data mock
        def load_qa_side_effect(company_name):
            if company_name == "Company1":
                return qa_items_company1
            elif company_name == "Company2":
                return qa_items_company2
            elif company_name == "Company3": # Simulate a company with no data
                return []
            return []
        mock_load_qa.side_effect = load_qa_side_effect

        # Mock collections for each company
        mock_collection_c1 = MagicMock(name="CollectionC1")
        mock_collection_c2 = MagicMock(name="CollectionC2")
        mock_collection_c3 = MagicMock(name="CollectionC3") # For Company3

        def get_collection_side_effect(company_name):
            if company_name == "Company1":
                return mock_collection_c1
            elif company_name == "Company2":
                return mock_collection_c2
            elif company_name == "Company3":
                return mock_collection_c3
            return MagicMock() # Default mock
        mock_get_create_collection.side_effect = get_collection_side_effect

        # Call the function to test
        companies_to_test = ["Company1", "Company2", "Company3"]
        with patch('app.utils.companies', companies_to_test): # Temporarily override companies list in utils
             load_all_qa_into_chroma()


        # Assertions for Company1
        mock_load_qa.assert_any_call("Company1")
        mock_get_create_collection.assert_any_call("Company1")
        expected_ids_c1 = [qa.id for qa in qa_items_company1]
        expected_docs_c1 = [qa.question for qa in qa_items_company1]
        expected_meta_c1 = [qa.to_dict() for qa in qa_items_company1]
        mock_collection_c1.upsert.assert_called_once_with(
            ids=expected_ids_c1,
            documents=expected_docs_c1,
            metadatas=expected_meta_c1
        )

        # Assertions for Company2
        mock_load_qa.assert_any_call("Company2")
        mock_get_create_collection.assert_any_call("Company2")
        expected_ids_c2 = [qa.id for qa in qa_items_company2]
        expected_docs_c2 = [qa.question for qa in qa_items_company2]
        expected_meta_c2 = [qa.to_dict() for qa in qa_items_company2]
        mock_collection_c2.upsert.assert_called_once_with(
            ids=expected_ids_c2,
            documents=expected_docs_c2,
            metadatas=expected_meta_c2
        )

        # Assertions for Company3 (no data, so no upsert)
        mock_load_qa.assert_any_call("Company3")
        mock_get_create_collection.assert_any_call("Company3")
        mock_collection_c3.upsert.assert_not_called()


    @patch('app.utils.sentence_transformer_ef', new=None) # Simulate EF not available
    @patch('builtins.print') # To capture print output
    def test_load_all_qa_into_chroma_no_ef(self, mock_print):
        load_all_qa_into_chroma()
        mock_print.assert_any_call("SentenceTransformerEmbeddingFunction not initialized. Cannot load Q&A into ChromaDB.")


if __name__ == '__main__':
    unittest.main()
