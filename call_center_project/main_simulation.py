import asyncio
import os
import sys

# Add src to Python path to allow direct imports from src.module
# This assumes main_simulation.py is in the call_center_project directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.call_handling.call_handler import CallHandler

# Define default paths for data (used by services)
DEFAULT_KB_PATH = "data/knowledge_base"
DEFAULT_NLU_MODEL_PATH = "models/nlu" # RasaNLUParser expects a directory

# Dummy data files that kb_service.py expects
DUMMY_FAQS_FILE = os.path.join(DEFAULT_KB_PATH, "faqs.yml")
DUMMY_SOLUTIONS_FILE = os.path.join(DEFAULT_KB_PATH, "solutions.yml")

# Content for dummy YAML files (valid empty YAML)
EMPTY_FAQS_CONTENT = """
faqs:
  - id: faq_dummy_greeting
    intent: greet
    question_variants:
      - "Hello"
    answer: "Hello from dummy KB! How can I help?"
    tags: ["greeting"]
"""

EMPTY_SOLUTIONS_CONTENT = """
solutions:
  - id: sol_dummy_problem
    problem_description: "A dummy problem"
    related_intent: report_issue
    steps:
      - text: "This is a dummy solution step 1."
      - text: "This is a dummy solution step 2."
    tags: ["dummy", "troubleshooting"]
"""


def ensure_placeholder_data_exists():
    """
    Creates dummy directories and data files if they don't exist,
    to allow placeholder services to initialize without I/O errors.
    """
    print("Ensuring placeholder data and model directories exist...")
    os.makedirs(DEFAULT_KB_PATH, exist_ok=True)
    os.makedirs(DEFAULT_NLU_MODEL_PATH, exist_ok=True) # For RasaNLUParser

    if not os.path.exists(DUMMY_FAQS_FILE):
        with open(DUMMY_FAQS_FILE, "w") as f:
            f.write(EMPTY_FAQS_CONTENT)
        print(f"Created dummy FAQ file: {DUMMY_FAQS_FILE}")

    if not os.path.exists(DUMMY_SOLUTIONS_FILE):
        with open(DUMMY_SOLUTIONS_FILE, "w") as f:
            f.write(EMPTY_SOLUTIONS_CONTENT)
        print(f"Created dummy solutions file: {DUMMY_SOLUTIONS_FILE}")

    # RasaNLUParser's __init__ has a print statement for the model path,
    # but doesn't actually load anything in placeholder mode, so just the dir is enough.
    # If it tried to load files, we'd need dummy model files in models/nlu/.
    print("Placeholder data check complete.")


async def main():
    print("Starting Call Center Simulation...")

    # Setup dummy data so services relying on file paths don't crash
    ensure_placeholder_data_exists()

    call_handler_service = CallHandler()
    # The CallHandler initializes all services (STT, TTS, NLU, KB, ResponseGenerator)
    # using their default placeholder configurations.

    # Simulate one full call flow. The CallSession has a predefined script of 3 user inputs.
    await call_handler_service.run_simulation(number_of_calls=1)

    print("\nCall Center Simulation Finished.")

if __name__ == "__main__":
    # This structure allows the script to be run directly.
    # `asyncio.run` is the standard way to run an async main function.
    asyncio.run(main())
