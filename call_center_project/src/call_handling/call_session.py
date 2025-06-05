import asyncio
from src.services.speech_to_text.google_cloud_stt import GoogleCloudSTT
from src.services.text_to_speech.google_cloud_tts import GoogleCloudTTS
from src.bot_logic.nlu.rasa_nlu_parser import RasaNLUParser
from src.bot_logic.knowledge_base.kb_service import KnowledgeBaseService
from src.bot_logic.response_generator import ResponseGenerator

class CallSession:
    def __init__(self, session_id, stt_service: GoogleCloudSTT, tts_service: GoogleCloudTTS,
                 nlu_parser: RasaNLUParser, kb_service: KnowledgeBaseService, response_generator: ResponseGenerator):
        self.session_id = session_id
        self.stt_service = stt_service
        self.tts_service = tts_service
        self.nlu_parser = nlu_parser
        self.kb_service = kb_service # Though RG uses it, session might need direct access for complex logic
        self.response_generator = response_generator
        self.conversation_state = {}
        self.is_active = True
        self._mock_user_inputs_store = [ # Store of inputs for the session
            ("Hello", b'fake_audio_for_hello'),
            ("Is my internet down?", b'fake_audio_for_internet_status'),
            ("Goodbye", b'fake_audio_for_goodbye'),
        ]
        self._current_input_index = 0
        print(f"CallSession {self.session_id}: Initialized.")

    async def handle_call(self):
        """Manages the entire lifecycle of a call."""
        print(f"CallSession {self.session_id}: Handling call.")
        await self.play_greeting()

        while self.is_active:
            # 1. Get audio from user (simulated here)
            user_audio_chunk = await self._simulate_get_user_audio() # Now only gets audio
            if not user_audio_chunk:
                print(f"CallSession {self.session_id}: No more audio from user or call ended by simulation.")
                self.is_active = False
                break

            # 2. Transcribe user audio
            async def audio_stream_gen(chunk):
                yield chunk

            transcribed_text_from_stt = ""
            async for stt_result in self.stt_service.transcribe_stream(audio_stream_gen(user_audio_chunk), settings={'language_code': 'en-US'}):
                transcribed_text_from_stt = stt_result.get("transcript", "").strip()
                if stt_result.get("is_final"):
                    break

            if not transcribed_text_from_stt: # If STT output is empty
                print(f"CallSession {self.session_id}: STT produced no text. Asking user to repeat.")
                await self._play_bot_audio("Sorry, I didn't quite catch that. Could you please say it again?")
                continue # Skip to next loop iteration to get new audio

            effective_input_for_nlu = transcribed_text_from_stt # Use STT output for NLU
            print(f"CallSession {self.session_id}: Using STT output for NLU: '{effective_input_for_nlu}'.")

            # 3. Process with NLU
            nlu_output = await self.nlu_parser.parse(effective_input_for_nlu)
            print(f"CallSession {self.session_id}: NLU Output: {nlu_output}")

            if nlu_output.get('intent', {}).get('name') == 'goodbye':
                self.is_active = False # Mark inactive, response will be generated, then loop terminates

            # 4. Generate bot response text
            bot_response_text = self.response_generator.generate_response(nlu_output, self.conversation_state)
            print(f"CallSession {self.session_id}: Bot response (text): {bot_response_text}")

            # 5. Synthesize bot response to audio and play it
            await self._play_bot_audio(bot_response_text)

            # 6. Update conversation state based on response (simplified)
            # This is a very basic way to manage state for the placeholder; real systems are more complex.
            if self.is_active: # Only update state if call is still active
                if nlu_output.get('intent', {}).get('name') == 'report_issue' and \
                   self.kb_service.find_solution(nlu_output['intent']['name'], nlu_output.get('entities')):
                    solution_details = self.kb_service.find_solution(nlu_output['intent']['name'], nlu_output.get('entities'))
                    if solution_details and solution_details.get('id') and len(solution_details.get('steps', [])) > 1:
                        self.conversation_state['current_solution_id'] = solution_details['id']
                        self.conversation_state['current_step_index'] = 1 # Start with the second step next time
                        print(f"CallSession {self.session_id}: State updated - solution '{solution_details['id']}' started.")
                elif not self.conversation_state.get('current_solution_id'): # If not starting a new solution and no solution active
                    self.conversation_state.pop('current_solution_id', None)
                    self.conversation_state.pop('current_step_index', None)

            if not self.is_active and nlu_output.get('intent', {}).get('name') == 'goodbye':
                 # If intent was goodbye, loop will break after this iteration.
                 pass

        # After the loop, if the call was active for some interaction:
        # Check if we went through at least one mock input, implying some interaction.
        # The original _mock_user_inputs_store has 3 items.
        # If _current_input_index > 0, it means at least one input was processed.
        if self._current_input_index > 0 and self._current_input_index <= len(self._mock_user_inputs_store) :
            # Check if the call didn't end abruptly due to running out of inputs before a "goodbye"
            # or if the last intent wasn't "goodbye" already handled inside the loop.
            # This condition ensures feedback is asked unless the user explicitly said goodbye as the last step.
            if self.is_active or nlu_output.get('intent', {}).get('name') != 'goodbye':
                 await self._ask_and_log_feedback()

        await self.play_goodbye()
        print(f"CallSession {self.session_id}: Call processing finished.")

    async def _ask_and_log_feedback(self):
        feedback_question = "Before you go, would you say you were satisfied with the help today? Yes or No?"
        print(f"CallSession {self.session_id}: Asking for feedback: {feedback_question}")
        await self._play_bot_audio(feedback_question)

        # Simulate getting user's spoken feedback
        await asyncio.sleep(0.2) # Simulate user thinking
        # For this simulation, we'll use a fixed feedback response.
        # In a real system, this would be dynamic and come from the telephony/STT pipeline.
        # Let's assume user says "Yes, I was satisfied"
        # The STT placeholder will return its canned response, but we'll parse based on common positive/negative terms.
        simulated_feedback_audio_chunk = b'fake_audio_for_yes_feedback' # This audio chunk is not used by mock STT

        feedback_text_from_stt = ""
        async def feedback_audio_stream(chunk):
            yield chunk

        # We'll use a canned STT response for feedback to test parsing,
        # as the current STT mock gives fixed output regardless of input audio.
        # Let's simulate STT returning "yes I was satisfied"
        # To do this more cleanly, one might enhance STT mock or this feedback simulation.
        # For now, we'll assume STT gives something reasonable for feedback.
        # The STT mock returns "Hello world this is a test." - let's use that and see parsing.
        # A better approach for testing would be to have STT mock return varied text.
        # Forcing a mock text for feedback:
        mock_stt_feedback_response = "yes, I was satisfied" # Forcing this for testing feedback parsing

        # Simulate STT processing for feedback
        # async for stt_result in self.stt_service.transcribe_stream(feedback_audio_stream(simulated_feedback_audio_chunk)):
        #     feedback_text_from_stt = stt_result.get("transcript", "").lower()
        #     if stt_result.get("is_final"):
        #         break
        # Instead of real STT call for feedback, using forced text:
        feedback_text_from_stt = mock_stt_feedback_response.lower()


        # Simple parsing of feedback
        parsed_feedback = "unknown"
        if "yes" in feedback_text_from_stt or "yeah" in feedback_text_from_stt or "satisfied" in feedback_text_from_stt:
            parsed_feedback = "satisfied"
        elif "no" in feedback_text_from_stt or "not really" in feedback_text_from_stt or "unsatisfied" in feedback_text_from_stt:
            parsed_feedback = "unsatisfied"

        print(f"CallSession {self.session_id}: User feedback (simulated text): '{feedback_text_from_stt}', Parsed as: {parsed_feedback}")
        self.log_feedback(parsed_feedback)

    def log_feedback(self, feedback_data):
        # Using asyncio.get_event_loop().time() for a simple timestamp.
        # For human-readable, datetime module would be better.
        timestamp = asyncio.get_event_loop().time()
        log_entry = f"SessionID: {self.session_id}, Timestamp: {timestamp:.2f}, Feedback: {feedback_data}\n"
        print(f"CallSession {self.session_id}: Logging feedback - {log_entry.strip()}")

        # Append to feedback_log.txt in the call_center_project directory
        # Ensure call_center_project directory is the CWD when main_simulation.py is run.
        feedback_file_path = "feedback_log.txt" # Assumes it's in call_center_project/

        try:
            # To ensure it's in the project root, we could use an absolute path if needed,
            # but main_simulation.py is in call_center_project, so this should be fine.
            with open(feedback_file_path, "a") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"CallSession {self.session_id}: Error writing to {feedback_file_path}: {e}")

    async def _simulate_get_user_audio(self):
        """Simulates receiving an audio chunk from the user. Returns a mock audio chunk or None."""
        await asyncio.sleep(0.2) # Simulate user thinking/speaking time
        if self._current_input_index < len(self._mock_user_inputs_store):
            # The text part of _mock_user_inputs_store is now effectively a comment for this method's simulation purpose
            _text_comment, audio_chunk = self._mock_user_inputs_store[self._current_input_index]
            self._current_input_index += 1
            # print(f"CallSession {self.session_id}: Simulating providing audio chunk: {audio_chunk}")
            return audio_chunk
        # print(f"CallSession {self.session_id}: No more simulated audio chunks.")
        return None # Simulate user hanging up or end of scripted input

    async def play_greeting(self):
        print(f"CallSession {self.session_id}: Playing greeting.")
        await self._play_bot_audio("Welcome to our automated service. How can I help you today?")

    async def play_goodbye(self):
        print(f"CallSession {self.session_id}: Playing goodbye message.")
        # Avoid playing goodbye if it was already part of the final response.
        # This simple check might need refinement.
        if self.conversation_state.get('last_bot_response') != "Goodbye! Have a great day.":
             await self._play_bot_audio("Thank you for calling. Goodbye!")

    async def _play_bot_audio(self, text_to_speak):
        """Simulates synthesizing text and playing it to the user."""
        print(f"CallSession {self.session_id}: Bot preparing to say: {text_to_speak}")
        self.conversation_state['last_bot_response'] = text_to_speak # Store last response for context
        audio_content = self.tts_service.synthesize_speech(text_to_speak)
        if audio_content:
            print(f"CallSession {self.session_id}: (Simulated playing {len(audio_content)} bytes of audio for '{text_to_speak[:30]}...')")
            await asyncio.sleep(0.5) # Simulate audio playback time
        else:
            print(f"CallSession {self.session_id}: TTS failed to produce audio for: {text_to_speak}")
