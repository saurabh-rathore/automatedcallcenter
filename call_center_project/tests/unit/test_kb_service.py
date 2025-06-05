import unittest
import os
import yaml
# Ensure src is discoverable for imports if tests are run from project root
import sys
# Adjust path to go up two levels from tests/unit to call_center_project, then into src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.bot_logic.knowledge_base.kb_service import KnowledgeBaseService

class TestKnowledgeBaseService(unittest.TestCase):

    def setUp(self):
        """Set up a temporary KB for testing."""
        # Ensure the path is relative to where the test is run from,
        # or use absolute paths based on this file's location.
        # If tests are run from project root, this path is fine.
        # If run from tests/unit, it's also fine.
        self.base_dir = os.path.dirname(__file__) # tests/unit
        self.test_kb_dir = os.path.join(self.base_dir, "temp_kb_data")
        os.makedirs(self.test_kb_dir, exist_ok=True)

        self.faqs_data = {
            'faqs': [
                {'id': 'faq1', 'intent': 'get_info', 'entities': [{'type': 'product'}], 'answer': 'Product info here'},
                {'id': 'faq2', 'intent': 'get_price', 'answer': 'Price info here'} # No entities
            ]
        }
        self.solutions_data = {
            'solutions': [
                {'id': 'sol1', 'related_intent': 'fix_issue', 'steps': [{'text': 'Step 1'}]}
            ]
        }
        with open(os.path.join(self.test_kb_dir, "faqs.yml"), 'w') as f:
            yaml.dump(self.faqs_data, f)
        with open(os.path.join(self.test_kb_dir, "solutions.yml"), 'w') as f:
            yaml.dump(self.solutions_data, f)

        # Initialize service with the path to the temp directory
        self.kb_service = KnowledgeBaseService(kb_directory=self.test_kb_dir)

    def tearDown(self):
        """Clean up temporary KB files."""
        if os.path.exists(self.test_kb_dir):
            for item in os.listdir(self.test_kb_dir):
                os.remove(os.path.join(self.test_kb_dir, item))
            os.rmdir(self.test_kb_dir)

    def test_load_faqs(self):
        self.assertEqual(len(self.kb_service.faqs), 2)
        self.assertEqual(self.kb_service.faqs[0]['id'], 'faq1')

    def test_load_solutions(self):
        self.assertEqual(len(self.kb_service.solutions), 1)
        self.assertEqual(self.kb_service.solutions[0]['id'], 'sol1')

    def test_find_faq_by_intent_no_entities_in_faq(self):
        # FAQ 'faq2' (get_price) has no entities defined for it.
        answer = self.kb_service.find_faq(intent_name='get_price', entities=[]) # NLU provides no entities
        self.assertEqual(answer, 'Price info here')
        answer_with_nlu_entities = self.kb_service.find_faq(intent_name='get_price', entities=[{'entity':'color', 'value':'blue'}]) # NLU provides entities
        self.assertEqual(answer_with_nlu_entities, 'Price info here') # Should still match as FAQ itself needs no entities

    def test_find_faq_with_entities_match(self):
        # FAQ 'faq1' (get_info) requires entity {'type': 'product'}
        # The kb_service.find_faq expects NLU entity format: {'entity': 'type', 'value': 'product'}
        answer = self.kb_service.find_faq(intent_name='get_info', entities=[{'entity':'type', 'value':'product'}])
        self.assertEqual(answer, 'Product info here')

    def test_find_faq_with_entities_no_nlu_entities(self):
        # FAQ 'faq1' (get_info) requires entity, but NLU provides none.
        answer = self.kb_service.find_faq(intent_name='get_info', entities=None) # or entities=[]
        self.assertIsNone(answer)
        answer_empty_list = self.kb_service.find_faq(intent_name='get_info', entities=[])
        self.assertIsNone(answer_empty_list)

    def test_find_faq_with_entities_mismatch(self):
        # FAQ 'faq1' (get_info) requires {'type': 'product'}, NLU provides different entity value.
        answer = self.kb_service.find_faq(intent_name='get_info', entities=[{'entity':'type', 'value':'service'}])
        self.assertIsNone(answer)
        # NLU provides different entity key
        answer2 = self.kb_service.find_faq(intent_name='get_info', entities=[{'entity':'color', 'value':'product'}])
        self.assertIsNone(answer2)


    def test_find_faq_no_match_intent(self):
        answer = self.kb_service.find_faq(intent_name='unknown_intent')
        self.assertIsNone(answer)

    def test_find_solution_by_intent(self):
        solution_steps = self.kb_service.find_solution(intent_name='fix_issue')
        self.assertIsNotNone(solution_steps)
        self.assertEqual(len(solution_steps), 1)
        self.assertEqual(solution_steps[0]['text'], 'Step 1')

    def test_find_solution_no_match_intent(self):
        solution_steps = self.kb_service.find_solution(intent_name='unknown_problem')
        self.assertIsNone(solution_steps)

if __name__ == '__main__':
    unittest.main()
