import asyncio
import uuid
from .call_session import CallSession
from src.services.speech_to_text.google_cloud_stt import GoogleCloudSTT
from src.services.text_to_speech.google_cloud_tts import GoogleCloudTTS
from src.bot_logic.nlu.rasa_nlu_parser import RasaNLUParser
from src.bot_logic.knowledge_base.kb_service import KnowledgeBaseService
from src.bot_logic.response_generator import ResponseGenerator

class CallHandler:
    def __init__(self):
        # Initialize all shared services here
        # In a real app, these might be singletons or managed by a DI container
        # For NLU and KB, paths are relative to project root where main_simulation.py will run
        self.stt_service = GoogleCloudSTT()
        self.tts_service = GoogleCloudTTS()
        self.nlu_parser = RasaNLUParser(model_path="models/nlu")
        self.kb_service = KnowledgeBaseService(kb_directory="data/knowledge_base/")
        self.response_generator = ResponseGenerator(self.kb_service)
        self.active_sessions = {}
        print("CallHandler initialized with all services.")

    async def handle_incoming_call(self):
        """Simulates an incoming call and starts a new session."""
        session_id = str(uuid.uuid4())
        print(f"CallHandler: Incoming call, assigning session ID {session_id}")

        # Create a new CallSession with all the services
        session = CallSession(
            session_id=session_id,
            stt_service=self.stt_service,
            tts_service=self.tts_service,
            nlu_parser=self.nlu_parser,
            kb_service=self.kb_service,
            response_generator=self.response_generator
        )

        self.active_sessions[session_id] = session
        try:
            await session.handle_call()
        except Exception as e:
            print(f"CallHandler: Error during call session {session_id}: {e}")
            # Potentially log the error more formally
        finally:
            # Clean up session after call is done or if an error occurred
            self.active_sessions.pop(session_id, None)
            print(f"CallHandler: Session {session_id} ended and cleaned up.")

    async def run_simulation(self, number_of_calls=1):
        """Runs a simulation of handling a number of calls sequentially."""
        print(f"CallHandler: Starting simulation for {number_of_calls} call(s).")
        for i in range(number_of_calls):
            print(f"\n--- Simulating Call {i+1} of {number_of_calls} ---")
            await self.handle_incoming_call()
            if i < number_of_calls - 1:
                print("--- Call Finished ---")
                await asyncio.sleep(1) # Brief pause between simulated calls
            else:
                print("--- Final Call Finished ---")
        print("\nCallHandler: Simulation finished.")
