# Placeholder for Response Generation Logic
from .knowledge_base.kb_service import KnowledgeBaseService # Assuming it's available
# We won't directly call NLU here, but expect its output as input

class ResponseGenerator:
    def __init__(self, kb_service: KnowledgeBaseService):
        """Initialize the Response Generator."""
        self.kb_service = kb_service
        print("ResponseGenerator initialized.")

    def generate_response(self, nlu_output, conversation_state=None):
        """
        Generates a response based on NLU output and KB results.

        Args:
            nlu_output: Dictionary from the NLU parser
                        (e.g., {'intent': {'name': 'greet', 'confidence': 0.95}, 'entities': []}).
            conversation_state: Optional dictionary to hold conversation context (e.g., current solution steps).

        Returns:
            A string containing the bot's response.
        """
        intent_name = nlu_output.get('intent', {}).get('name')
        entities = nlu_output.get('entities', [])
        # confidence = nlu_output.get('intent', {}).get('confidence', 0.0)

        if not conversation_state:
            conversation_state = {}

        response_text = "I'm sorry, I didn't quite understand that. Could you please rephrase?"

        # 1. Handle ongoing multi-step solutions first
        current_solution_id = conversation_state.get('current_solution_id')
        current_step_index = conversation_state.get('current_step_index', 0)

        if current_solution_id:
            # This is a simplified continuation logic.
            # Real logic would depend on user's response to previous step.
            solution = self._get_solution_by_id(current_solution_id) # Helper needed
            if solution and current_step_index < len(solution['steps']):
                next_step = solution['steps'][current_step_index]
                response_text = next_step['text']
                # The main bot loop would typically update conversation_state['current_step_index']
                # For this function, we are just returning the text for the current step.
                return response_text # Early exit if handling a solution step
            else:
                # Solution finished or invalid state, clear it from context for the next turn
                # This should ideally be handled by the main bot loop after this response is sent.
                conversation_state.pop('current_solution_id', None)
                conversation_state.pop('current_step_index', None)

        # 2. Standard intent-based responses
        if intent_name == 'greet':
            response_text = "Hello! How can I help you today?"
        elif intent_name == 'goodbye':
            response_text = "Goodbye! Have a great day."
        elif intent_name == 'thank_you':
            response_text = "You're welcome! Is there anything else I can assist you with?"
        elif intent_name:
            # Try to find an FAQ first
            faq_answer = self.kb_service.find_faq(intent_name, entities)
            if faq_answer:
                response_text = faq_answer
            else:
                # Try to find a solution if no FAQ matched
                solution_details = self.kb_service.find_solution(intent_name, entities) # Assuming find_solution returns the whole solution dict or None
                if solution_details and solution_details.get('steps'):
                    first_step = solution_details['steps'][0]
                    response_text = first_step['text']
                    # The main bot orchestrator would use solution_details.get('id') and set current_step_index = 1
                    # in conversation_state if this is the start of a solution.
                    # For example:
                    # conversation_state['current_solution_id'] = solution_details.get('id')
                    # conversation_state['current_step_index'] = 1 # To indicate next step is step 1
                else:
                    response_text = f"I understand you're asking about '{intent_name}', but I don't have specific information on that yet. I can connect you to an agent if you'd like."

        return response_text

    def _get_solution_by_id(self, solution_id):
        """Helper to retrieve a full solution from KB by its ID."""
        for sol in self.kb_service.solutions:
            if sol.get('id') == solution_id:
                return sol
        return None

# Example usage (for testing this module directly)
if __name__ == '__main__':
    # This requires the KnowledgeBaseService and its data files to be accessible
    # Adjust path if running from a different directory.
    # Assumes project root is the current working directory.
    kb_service = KnowledgeBaseService(kb_directory="data/knowledge_base/")
    response_gen = ResponseGenerator(kb_service)

    test_cases = [
        ({'intent': {'name': 'greet', 'confidence': 0.99}, 'entities': []}, "Greeting"),
        ({'intent': {'name': 'ask_service_status', 'confidence': 0.92},
          'entities': [{'entity': 'service_type', 'value': 'internet'}]}, "Ask service status (internet) - no specific FAQ/Solution for this intent alone"),
        ({'intent': {'name': 'get_billing_info', 'confidence': 0.9},
          'entities': [{'entity':'billing_property', 'value':'due_date'}]}, "FAQ for billing due date"),
        ({'intent': {'name': 'report_issue', 'confidence': 0.88},
          'entities': [{'entity':'service_type', 'value':'internet'}, {'entity':'issue_type', 'value':'no_connection'}]}, "Start Solution for no internet"),
        ({'intent': {'name': 'unknown_intent_example', 'confidence': 0.5}, 'entities': []}, "Unknown intent"),
        ({'intent': {'name': 'goodbye', 'confidence': 0.99}, 'entities': []}, "Goodbye"),
    ]

    conversation_context = {} # Simulate conversation state
    print("--- Running Single Turn Test Cases ---")
    for nlu_data, description in test_cases:
        print(f"Test Case: {description}")
        print(f"  NLU: {nlu_data}")
        # Make a copy of context for this specific call if needed, or manage it outside
        current_context_for_call = dict(conversation_context)
        response = response_gen.generate_response(nlu_data, current_context_for_call)
        print(f"  Bot: {response}")

        # --- Simulation of how a bot orchestrator might update context ---
        # This logic is EXTERNAL to ResponseGenerator, but shown here for testing flow
        intent_name = nlu_data.get('intent', {}).get('name')
        entities = nlu_data.get('entities', [])

        # Clear old solution context if it's not a continuation
        if not current_context_for_call.get('current_solution_id') or intent_name not in ['generic_reply', None]: # Assuming generic_reply for continuation
             conversation_context.pop('current_solution_id', None)
             conversation_context.pop('current_step_index', None)

        if intent_name and not response_gen.kb_service.find_faq(intent_name, entities):
            solution_details = response_gen.kb_service.find_solution(intent_name, entities)
            if solution_details and solution_details.get('steps'):
                is_starting_solution = True # Simplified check
                if is_starting_solution and len(solution_details['steps']) > 1: # If it's a multi-step solution
                    conversation_context['current_solution_id'] = solution_details['id']
                    conversation_context['current_step_index'] = 1 # Next step is step 1 (0-indexed)
                    print(f"  (Orchestrator: Context set for solution '{solution_details['id']}', next step index: 1)")
        # --- End of Orchestrator Simulation ---
        print("---")

    print("\n--- Running Multi-Turn Solution Test ---")
    # 1. Initial problem report - starts the solution
    nlu_problem = {'intent': {'name': 'report_issue', 'confidence': 0.88},
                   'entities': [{'entity':'service_type', 'value':'internet'}, {'entity':'issue_type', 'value':'no_connection'}]}
    print(f"Turn 1: User reports problem")
    print(f"  NLU: {nlu_problem}")
    context_turn1 = {} # Fresh context
    response1 = response_gen.generate_response(nlu_problem, context_turn1)
    print(f"  Bot: {response1}")

    # Orchestrator updates context
    solution_details_t1 = response_gen.kb_service.find_solution(nlu_problem['intent']['name'], nlu_problem['entities'])
    if solution_details_t1 and len(solution_details_t1.get('steps', [])) > 1:
        context_turn1['current_solution_id'] = solution_details_t1['id']
        context_turn1['current_step_index'] = 1
        print(f"  (Orchestrator: Context set to {context_turn1})")
    print("---")

    # 2. User gives a generic reply (e.g., "okay"), bot should give next step
    if context_turn1.get('current_solution_id'): # If a solution is in progress
        nlu_continue = {'intent': {'name': 'generic_reply', 'confidence': 0.7}, 'entities': []} # User says "okay"
        print(f"Turn 2: User says 'okay'")
        print(f"  NLU: {nlu_continue}")
        print(f"  Context IN: {context_turn1}")
        response2 = response_gen.generate_response(nlu_continue, context_turn1) # Pass the existing context
        print(f"  Bot: {response2}")

        # Orchestrator updates context
        if context_turn1.get('current_solution_id'): # Check if solution is still active
            solution_obj = response_gen._get_solution_by_id(context_turn1['current_solution_id'])
            if solution_obj and context_turn1['current_step_index'] < len(solution_obj['steps']) -1:
                 context_turn1['current_step_index'] += 1
                 print(f"  (Orchestrator: Context updated to {context_turn1})")
            else:
                 print(f"  (Orchestrator: Solution ended or at last step. Context cleared.)")
                 context_turn1.pop('current_solution_id', None)
                 context_turn1.pop('current_step_index', None)

        print("---")

        # 3. User gives another generic reply, bot should give next step or end
        if context_turn1.get('current_solution_id'):
            nlu_continue2 = {'intent': {'name': 'generic_reply_again', 'confidence': 0.7}, 'entities': []}
            print(f"Turn 3: User says 'done that'")
            print(f"  NLU: {nlu_continue2}")
            print(f"  Context IN: {context_turn1}")
            response3 = response_gen.generate_response(nlu_continue2, context_turn1)
            print(f"  Bot: {response3}")
            # Orchestrator update simulation
            if context_turn1.get('current_solution_id'):
                solution_obj = response_gen._get_solution_by_id(context_turn1['current_solution_id'])
                if solution_obj and context_turn1['current_step_index'] < len(solution_obj['steps']) -1:
                    context_turn1['current_step_index'] += 1
                    print(f"  (Orchestrator: Context updated to {context_turn1})")
                else:
                    print(f"  (Orchestrator: Solution ended or at last step. Context cleared.)")
                    context_turn1.pop('current_solution_id', None)
                    context_turn1.pop('current_step_index', None)
            print("---")
