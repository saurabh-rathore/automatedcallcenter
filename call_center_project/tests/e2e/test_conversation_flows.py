import unittest
import asyncio
import os
import sys
import yaml # For creating dummy KB files for the test

# Ensure src is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.call_handling.call_handler import CallHandler
from src.bot_logic.nlu.rasa_nlu_parser import RasaNLUParser # To potentially mock NLU behavior further if needed
from src.services.speech_to_text.google_cloud_stt import GoogleCloudSTT
from src.services.text_to_speech.google_cloud_tts import GoogleCloudTTS

# Define paths for dummy data specific to these E2E tests
E2E_TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "e2e_test_data")
E2E_KB_DIR = os.path.join(E2E_TEST_DATA_DIR, "knowledge_base")
E2E_NLU_MODELS_DIR = os.path.join(E2E_TEST_DATA_DIR, "models", "nlu")

# Dummy FAQ content for E2E test
E2E_FAQ_CONTENT = {
    'faqs': [
        {'id': 'e2e_faq_greet', 'intent': 'greet', 'answer': 'Hello from E2E test bot!'},
        {'id': 'e2e_faq_internet', 'intent': 'ask_internet_plan', 'answer': 'We offer E2E Basic and E2E Premium internet.'},
        {'id': 'e2e_faq_goodbye', 'intent': 'goodbye', 'answer': 'E2E Goodbye!'} # Response Generator might override this
    ]
}
# Dummy Solution content for E2E test
E2E_SOLUTIONS_CONTENT = {
    'solutions': [
        {'id': 'e2e_sol_problem', 'related_intent': 'report_e2e_problem', 'steps': [{'text': 'E2E Solution: Step 1.'}]}
    ]
}
# Dummy NLU mock responses for this E2E test
E2E_NLU_MOCK_RESPONSES = {
    "hello test": {"intent": {"name": "greet", "confidence": 0.99}, "entities": []},
    "tell me about e2e internet": {"intent": {"name": "ask_internet_plan", "confidence": 0.92}, "entities": []},
    "i have an e2e problem": {"intent": {"name": "report_e2e_problem", "confidence": 0.88}, "entities": []},
    "e2e goodbye now": {"intent": {"name": "goodbye", "confidence": 0.95}, "entities": []},
}


class TestConversationFlows(unittest.IsolatedAsyncioTestCase): # Using IsolatedAsyncioTestCase for async tests

    def setUp(self):
        """Setup dummy data and directories for E2E tests."""
        os.makedirs(E2E_KB_DIR, exist_ok=True)
        os.makedirs(E2E_NLU_MODELS_DIR, exist_ok=True) # For NLU parser's model_path

        with open(os.path.join(E2E_KB_DIR, "faqs.yml"), 'w') as f:
            yaml.dump(E2E_FAQ_CONTENT, f)
        with open(os.path.join(E2E_KB_DIR, "solutions.yml"), 'w') as f:
            yaml.dump(E2E_SOLUTIONS_CONTENT, f)

        # The CallHandler will initialize services. We will mock parts of these services.
        self.call_handler_service = CallHandler()
        # Override KB and NLU paths for the handler's services to use our E2E test data
        self.call_handler_service.kb_service.kb_directory = E2E_KB_DIR
        self.call_handler_service.kb_service._load_knowledge_base() # Reload with test data

        self.call_handler_service.nlu_parser.model_path = E2E_NLU_MODELS_DIR # For consistency if NLU loaded files
        # Override NLU parser's mock responses for this test run
        self.original_nlu_mock_responses = self.call_handler_service.nlu_parser.mock_responses
        self.call_handler_service.nlu_parser.mock_responses = E2E_NLU_MOCK_RESPONSES

    def tearDown(self):
        """Clean up dummy data and directories."""
        # Restore original NLU mock responses if other tests use the same CallHandler instance (not typical for unittest)
        self.call_handler_service.nlu_parser.mock_responses = self.original_nlu_mock_responses

        if os.path.exists(E2E_TEST_DATA_DIR):
            for root, dirs, files in os.walk(E2E_TEST_DATA_DIR, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(E2E_TEST_DATA_DIR)


    async def run_simulated_call_with_script(self, user_text_script):
        """
        Helper to run a call simulation with a predefined sequence of user text inputs.
        Mocks STT to use these text inputs and captures TTS output text.
        """

        # Store original service methods to restore them later
        original_stt_transcribe_stream = self.call_handler_service.stt_service.transcribe_stream
        original_tts_synthesize_speech = self.call_handler_service.tts_service.synthesize_speech

        # Mock STT service to feed predefined text inputs
        async def mock_stt_transcribe_stream(audio_chunk_ignored, settings=None):
            if user_text_script:
                text = user_text_script.pop(0)
                # print(f"\nE2E STT Mock: Feeding text '{text}'")
                yield {"transcript": text, "is_final": True, "confidence": 0.98}
            else: # No more scripted input
                # print("\nE2E STT Mock: No more input, yielding empty.")
                yield {"transcript": "", "is_final": True, "confidence": 0.0}

        self.call_handler_service.stt_service.transcribe_stream = mock_stt_transcribe_stream

        # Capture bot responses (text passed to TTS)
        bot_tts_responses = []
        def mock_tts_synthesize_speech(text_input, voice_params=None, audio_config_params=None, output_filepath=None):
            # print(f"E2E TTS Mock: Capturing bot response '{text_input}'")
            bot_tts_responses.append(text_input)
            return b"mock_audio_bytes_for_e2e_test" # Return some bytes to satisfy TTS interface

        self.call_handler_service.tts_service.synthesize_speech = mock_tts_synthesize_speech

        # Run the call simulation using the CallHandler's method
        # The CallHandler creates a CallSession which will use the mocked STT/TTS
        await self.call_handler_service.handle_incoming_call()

        # Restore original service methods
        self.call_handler_service.stt_service.transcribe_stream = original_stt_transcribe_stream
        self.call_handler_service.tts_service.synthesize_speech = original_tts_synthesize_speech

        return bot_tts_responses

    async def test_greeting_faq_goodbye_flow(self):
        """Test a flow: Greeting -> User asks FAQ -> Bot answers from E2E KB -> User says Goodbye."""
        user_script = [
            "hello test",                 # Triggers 'greet' intent via E2E_NLU_MOCK_RESPONSES
            "tell me about e2e internet", # Triggers 'ask_internet_plan'
            "e2e goodbye now"             # Triggers 'goodbye'
        ]

        bot_responses = await self.run_simulated_call_with_script(user_script)

        # Expected sequence of bot's spoken responses:
        # 1. Initial Greeting from CallSession.play_greeting()
        # 2. Response to "hello test" (from ResponseGenerator, using E2E KB for 'greet' FAQ)
        # 3. Response to "tell me about e2e internet" (from E2E KB for 'ask_internet_plan' FAQ)
        # 4. Response to "e2e goodbye now" (from ResponseGenerator for 'goodbye' intent, might use E2E KB)
        # 5. Final Goodbye from CallSession.play_goodbye() (if not redundant)
        # 6. Potential feedback question if the logic triggers it.

        # Print responses for debugging during test development:
        # print("\nE2E Test Bot Responses:")
        # for i, r in enumerate(bot_responses): print(f"  {i+1}. {r}")

        self.assertIn("Welcome to our automated service. How can I help you today?", bot_responses[0])
        self.assertIn("Hello from E2E test bot!", bot_responses[1])
        self.assertIn("We offer E2E Basic and E2E Premium internet.", bot_responses[2])

        # ResponseGenerator's hardcoded 'goodbye' is "Goodbye! Have a great day."
        # If E2E KB had a 'goodbye' FAQ, RG would use that. Our E2E_FAQ_CONTENT has one.
        self.assertIn("E2E Goodbye!", bot_responses[3])

        # Check if feedback was asked. The last user intent was 'goodbye'.
        # The CallSession's feedback logic:
        # if self.is_active or nlu_output.get('intent', {}).get('name') != 'goodbye': await self._ask_and_log_feedback()
        # Since the last intent *is* 'goodbye', feedback should NOT be asked.
        feedback_question_text = "Before you go, would you say you were satisfied with the help today? Yes or No?"
        self.assertTrue(all(feedback_question_text not in r for r in bot_responses[4:]))

        # Final goodbye from CallSession.play_goodbye(). This might be redundant if RG already said goodbye.
        # Current play_goodbye: if self.conversation_state.get('last_bot_response') != "Goodbye! Have a great day.":
        # Since RG's response to 'goodbye' intent (from E2E KB) is "E2E Goodbye!", this condition is true.
        self.assertIn("Thank you for calling. Goodbye!", bot_responses[4])


if __name__ == '__main__':
    unittest.main()
