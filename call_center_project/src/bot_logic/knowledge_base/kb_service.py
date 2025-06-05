import yaml
import os

class KnowledgeBaseService:
    def __init__(self, kb_directory="data/knowledge_base/"):
        """Initialize the Knowledge Base service by loading data from YAML files."""
        self.kb_directory = kb_directory
        self.faqs = []
        self.solutions = []
        self._load_knowledge_base()
        print(f"KnowledgeBaseService initialized. Loaded {len(self.faqs)} FAQs and {len(self.solutions)} solutions.")

    def _load_knowledge_base(self):
        faq_file_path = os.path.join(self.kb_directory, "faqs.yml")
        solutions_file_path = os.path.join(self.kb_directory, "solutions.yml")

        try:
            if os.path.exists(faq_file_path):
                with open(faq_file_path, 'r') as f:
                    data = yaml.safe_load(f)
                    self.faqs = data.get('faqs', [])
            else:
                print(f"Warning: FAQ file not found at {faq_file_path}")
        except Exception as e:
            print(f"Error loading FAQs: {e}")

        try:
            if os.path.exists(solutions_file_path):
                with open(solutions_file_path, 'r') as f:
                    data = yaml.safe_load(f)
                    self.solutions = data.get('solutions', [])
            else:
                print(f"Warning: Solutions file not found at {solutions_file_path}")
        except Exception as e:
            print(f"Error loading solutions: {e}")

    def find_faq(self, intent_name, entities=None):
        """
        Finds an FAQ based on intent and optionally entities.
        This is a very basic matching logic for placeholder.
        Args:
            intent_name: The name of the intent from NLU.
            entities: A list of entities from NLU (e.g., [{'entity': 'service_type', 'value': 'internet'}])

        Returns:
            The answer string if a match is found, else None.
        """
        # More sophisticated matching would be needed in a real system
        # (e.g., matching multiple entities, partial matches, confidence scores)
        for faq in self.faqs:
            if faq.get('intent') == intent_name:
                faq_entity_requirements = faq.get('entities', [])

                if not faq_entity_requirements:  # FAQ has no entity requirements
                    return faq.get('answer')

                # FAQ has entity requirements, so NLU must provide entities for a match.
                if not entities:  # NLU provided no entities (None or empty list)
                    continue  # This FAQ requires entities, but none were provided by NLU. Skip to next FAQ.

                # Both FAQ and NLU have entities, proceed with matching.
                match_count = 0
                required_entities_in_faq = len(faq_entity_requirements) # Define required_entities_in_faq
                for faq_entity_req in faq_entity_requirements:
                    for nlu_entity in entities:
                        if list(faq_entity_req.keys())[0] == nlu_entity.get('entity') and \
                           list(faq_entity_req.values())[0] == nlu_entity.get('value'):
                            match_count += 1
                            break # Found this required FAQ entity in NLU entities

                if required_entities_in_faq > 0 and match_count == required_entities_in_faq: # Ensure it only returns if entities were required and matched
                    return faq.get('answer')
                # If required_entities_in_faq is 0, it should have been caught by the earlier "if not faq_entity_requirements:"
        return None

    def find_solution(self, intent_name, entities=None, current_issue_summary=""):
        """
        Finds a solution based on related intent, entities, or keywords.
        This is a very basic matching logic for placeholder.
        Args:
            intent_name: The intent from NLU (e.g., 'report_issue').
            entities: A list of entities from NLU.
            current_issue_summary: Text summary of the issue.

        Returns:
            A list of solution steps if a match is found, else None.
        """
        # Real matching would be more complex, potentially using keyword extraction from summary,
        # fuzzy matching, or even a small rule engine.
        for sol in self.solutions:
            if sol.get('related_intent') == intent_name:
                solution_entity_requirements = sol.get('related_entities', [])

                if not solution_entity_requirements: # Solution has no entity requirements
                    return sol.get('steps')

                # Solution has entity requirements, so NLU must provide entities.
                if not entities: # NLU provided no entities.
                    continue # Skip to next solution.

                # Both solution and NLU have entities, proceed with matching.
                match_count = 0
                required_entities_in_solution = len(solution_entity_requirements) # Define required_entities_in_solution
                for sol_entity_req in solution_entity_requirements:
                    for nlu_entity in entities:
                        if list(sol_entity_req.keys())[0] == nlu_entity.get('entity') and \
                           list(sol_entity_req.values())[0] == nlu_entity.get('value'):
                            match_count += 1
                            break

                if required_entities_in_solution > 0 and match_count == required_entities_in_solution: # Ensure it only returns if entities were required and matched
                    return sol.get('steps')
                # If required_entities_in_solution is 0, it should have been caught by "if not solution_entity_requirements:"
        return None

# Example usage
if __name__ == '__main__':
    # Assume this script is run from the root of call_center_project
    # If run from src/bot_logic/knowledge_base, change path accordingly
    # For example: KnowledgeBaseService(kb_directory="../../../data/knowledge_base/")
    kb_service = KnowledgeBaseService(kb_directory="data/knowledge_base/")

    print("\n--- Testing FAQ Retrieval ---")
    # Test case 1: Simple intent match with entities
    answer1 = kb_service.find_faq("get_billing_info", entities=[{'entity': 'billing_property', 'value': 'due_date'}])
    print(f"Q: When is my bill due? -> A: {answer1}")

    # Test case 2: Intent and multiple entity match
    answer2 = kb_service.find_faq("get_service_info", entities=[{'entity': 'service_type', 'value': 'internet'}, {'entity':'info_type', 'value':'plans'}])
    print(f"Q: Tell me about internet plans -> A: {answer2}")

    # Test case 3: No match (e.g. intent exists but entities don't match or are missing)
    answer3 = kb_service.find_faq("get_billing_info", entities=[{'entity': 'billing_property', 'value': 'wrong_value'}])
    print(f"Q: Billing info with wrong entity value -> A: {answer3}")

    answer4 = kb_service.find_faq("unknown_intent")
    print(f"Q: Unknown question -> A: {answer4}")

    print("\n--- Testing Solution Retrieval ---")
    # Test case 1: Intent and entity match for solution
    solution1 = kb_service.find_solution("report_issue", entities=[{'entity': 'service_type', 'value': 'internet'}, {'entity':'issue_type', 'value':'no_connection'}])
    print(f"P: No internet connection -> S: {solution1}")
    if solution1:
        for step in solution1:
            print(f"  - {step['text']}")

    # Test case 2: No match for solution (e.g. wrong entity value)
    solution2 = kb_service.find_solution("report_issue", entities=[{'entity': 'service_type', 'value': 'mobile'}, {'entity':'issue_type', 'value':'broken_screen'}])
    print(f"P: Broken mobile screen -> S: {solution2}")
