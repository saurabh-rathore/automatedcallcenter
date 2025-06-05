import os
import sys
import datetime
import logging
import json
import subprocess
import yaml # For KB management

# Adjust Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.services.speech_to_text.google_cloud_stt import GoogleCloudSTT # noqa

logger = logging.getLogger("AdminPortalApp")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UPLOAD_DIR_FOR_STT = os.path.join(PROJECT_ROOT, "data", "uploaded_for_stt")
FEEDBACK_LOG_FILE = os.path.join(PROJECT_ROOT, "feedback_log.txt")
ORCHESTRATOR_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "retrain_orchestrator.py")
ORCHESTRATION_SUMMARY_PATH = os.path.join(PROJECT_ROOT, "logs", "orchestration_summary.json")
KB_BASE_PATH = os.path.join(PROJECT_ROOT, "data", "knowledge_base")
FAQS_FILE_PATH = os.path.join(KB_BASE_PATH, "faqs.yml")
SOLUTIONS_FILE_PATH = os.path.join(KB_BASE_PATH, "solutions.yml")


# --- Authentication Placeholders ---
MOCK_USERS = {"admin": "password123", "user": "pass"}
mock_session = {}

# --- Metrics Helper Functions (remain the same) ---
def _calculate_avg_satisfaction():
    logger.debug(f"Calculating average satisfaction from: {FEEDBACK_LOG_FILE}")
    satisfied_count = 0; unsatisfied_count = 0
    try:
        if not os.path.exists(FEEDBACK_LOG_FILE): return "N/A"
        with open(FEEDBACK_LOG_FILE, 'r') as f:
            for line in f:
                if "Feedback: satisfied" in line: satisfied_count += 1
                elif "Feedback: unsatisfied" in line: unsatisfied_count += 1
        total_feedback = satisfied_count + unsatisfied_count
        if total_feedback == 0: return "N/A (No feedback yet)"
        satisfaction_percentage = (satisfied_count / total_feedback) * 100
        return f"{satisfaction_percentage:.1f}% ({total_feedback} responses)"
    except Exception as e: logger.exception(f"Error reading feedback log: {e}"); return "N/A (Error)"

def _get_simulated_call_volume_metrics():
    return {"total_calls_today": 150 + datetime.datetime.now().hour, "calls_handled_by_bot": 120 + datetime.datetime.now().minute // 2, "calls_escalated_to_human": 30 + datetime.datetime.now().second // 10}

def _get_simulated_nlu_metrics():
    common_intents_options = [[("ask_service_status",50),("report_issue",40),("get_billing_info",30)], [("get_billing_info",55),("ask_service_status",45),("thank_you",20)]]
    return {"common_intents": common_intents_options[datetime.datetime.now().minute % len(common_intents_options)], "fallback_rate_today_percent": 5.0 + (datetime.datetime.now().second / 60.0)}

# --- Conceptual Route Functions (Simulating Flask-like behavior) ---

def _render_base_template(page_title, content_html, nav_links_html=""):
    nav_section = "<p>Navigation: " + nav_links_html + "</p><hr>"
    return f"<html><head><title>{page_title} - Admin Portal</title></head><body>{nav_section}<div>{content_html}</div></body></html>"

def _get_nav_links_html():
    links = "<a href='/'>Dashboard</a> | <a href='/manage_recordings_stt'>Transcribed Recordings</a> | <a href='/nlu_management'>NLU Management</a> | <a href='/kb_management'>KB Management</a>"
    if mock_session.get('logged_in_user'):
        return f"{links} | User: {mock_session['logged_in_user']} (<a href='/logout'>Logout</a>)"
    else:
        return f"{links} | <a href='/login'>Login</a>"

def login_page():
    # ... (remains the same)
    logger.info("Serving login page (placeholder).")
    if mock_session.get('logged_in_user'):
        return _render_base_template("Login", "<p>You are already logged in. <a href='/'>Go to Dashboard</a></p>", _get_nav_links_html())
    login_form_html = """<h2>Login</h2><form action="/login" method="POST"><p><label for="username">Username:</label> <input type="text" id="username" name="username" value="admin"></p><p><label for="password">Password:</label> <input type="password" id="password" name="password" value="password123"></p><p><input type="submit" value="Login"></p></form>"""
    return _render_base_template("Login", login_form_html, _get_nav_links_html())


def handle_login(username, password):
    # ... (remains the same)
    logger.info(f"Attempting login for user: {username}")
    if username in MOCK_USERS and MOCK_USERS[username] == password:
        mock_session['logged_in_user'] = username; logger.info(f"User '{username}' logged in successfully.")
        return {"status": "success", "message": f"Welcome {username}!", "redirect_url": "/"}
    else:
        logger.warning(f"Login failed for user: {username}")
        return {"status": "failure", "message": "Invalid username or password."}

def handle_logout():
    # ... (remains the same)
    logged_in_user = mock_session.pop('logged_in_user', None)
    if logged_in_user: logger.info(f"User '{logged_in_user}' logged out.")
    return {"status": "success", "message": "Logged out.", "redirect_url": "/login"}


def dashboard():
    if not mock_session.get('logged_in_user'): return _render_base_template("Access Denied", "<h2>Access Denied</h2><p>Please <a href='/login'>login</a>.</p>", _get_nav_links_html())
    logger.info("Serving admin dashboard.")
    metrics = {**_get_simulated_call_volume_metrics(), **_get_simulated_nlu_metrics(), "avg_satisfaction_score_display": _calculate_avg_satisfaction()}
    common_intents_html = ''.join([f'<li>{intent}: {count}</li>' for intent, count in metrics['common_intents']])
    content = f"<h1>Admin Dashboard</h1><h2>Metrics</h2><p>Total Calls: {metrics['total_calls_today']}</p><p>Avg Satisfaction: {metrics['avg_satisfaction_score_display']}</p><ul>{common_intents_html}</ul>"
    return _render_base_template("Dashboard", content, _get_nav_links_html())

def manage_recordings_stt(is_post_request=False, file_to_upload_info=None, api_key_json_str_info=None):
    if not mock_session.get('logged_in_user'): return _render_base_template("Access Denied", "<h2>Access Denied</h2><p>Please <a href='/login'>login</a>.</p>", _get_nav_links_html())
    # ... (core logic remains, for brevity focusing on KB part now)
    content = "<h2>Manage Transcribed Recordings Placeholder</h2><p>(Content for listing and uploading STT recordings would go here)</p>"
    return _render_base_template("Manage Transcribed Recordings", content, _get_nav_links_html())

def view_transcript(transcript_filename):
    if not mock_session.get('logged_in_user'): return _render_base_template("Access Denied", "<h2>Access Denied</h2><p>Please <a href='/login'>login</a>.</p>", _get_nav_links_html())
    # ... (core logic remains)
    content = f"<h2>View Transcript: {transcript_filename} Placeholder</h2><p>(Transcript content would go here)</p>"
    return _render_base_template(f"View Transcript: {transcript_filename}", content, _get_nav_links_html())

def nlu_management_page():
    if not mock_session.get('logged_in_user'): return _render_base_template("Access Denied", "<h2>Access Denied</h2><p>Please <a href='/login'>login</a>.</p>", _get_nav_links_html())
    # ... (core logic remains)
    status_html = get_nlu_retraining_status(return_html_formatted=True)
    content = f"<h1>NLU Management</h1><form action='/trigger_nlu_retrain' method='POST'><button type='submit'>Retrain NLU</button></form><h3>Status:</h3><pre>{status_html}</pre>"
    return _render_base_template("NLU Management", content, _get_nav_links_html())

def trigger_nlu_retrain(orchestrator_args_list_from_form=None):
    if not mock_session.get('logged_in_user'): return {"status": "error", "message": "Access Denied."}
    # ... (core logic remains)
    logger.info(f"Triggering NLU Retrain by {mock_session.get('logged_in_user')}")
    command = [sys.executable, ORCHESTRATOR_SCRIPT_PATH];
    if orchestrator_args_list_from_form: command.extend(orchestrator_args_list_from_form)
    process = subprocess.Popen(command, cwd=PROJECT_ROOT)
    return {"status": "success", "message": "NLU retraining initiated.", "pid": process.pid}


def get_nlu_retraining_status(return_html_formatted=False):
    # ... (remains the same)
    if os.path.exists(ORCHESTRATION_SUMMARY_PATH):
        try:
            with open(ORCHESTRATION_SUMMARY_PATH, 'r') as f: status_data = json.load(f)
            if return_html_formatted: return json.dumps(status_data, indent=4)
            return status_data
        except Exception as e: return f"Error reading status: {e}" if return_html_formatted else {"status":"error", "message":f"Error: {e}"}
    return "No status summary found." if return_html_formatted else {"status":"unavailable", "message":"No status summary."}


# --- New KB Management Functions ---
def kb_management_page():
    if not mock_session.get('logged_in_user'): return _render_base_template("Access Denied", "<h2>Access Denied</h2><p>Please <a href='/login'>login</a>.</p>", _get_nav_links_html())
    logger.info("Serving KB Management page.")

    faqs_data = []
    solutions_data = []
    faqs_html_list = "<li>No FAQs found or error loading.</li>"
    solutions_html_list = "<li>No solutions found or error loading.</li>"

    try:
        if os.path.exists(FAQS_FILE_PATH):
            with open(FAQS_FILE_PATH, 'r') as f: faqs_data = yaml.safe_load(f).get('faqs', [])
        if faqs_data:
            faqs_html_list = "".join([f"<li>ID: {faq.get('id', 'N/A')} - Q: {faq.get('question_variants', ['N/A'])[0] if faq.get('question_variants') else 'N/A'} <a href='/kb/faq/edit/{faq.get('id')}'>Edit</a> | <a href='/kb/faq/delete/{faq.get('id')}'>Delete</a></li>" for faq in faqs_data])
    except Exception as e: logger.error(f"Error loading FAQs for KB management: {e}")

    try:
        if os.path.exists(SOLUTIONS_FILE_PATH):
            with open(SOLUTIONS_FILE_PATH, 'r') as f: solutions_data = yaml.safe_load(f).get('solutions', [])
        if solutions_data:
            solutions_html_list = "".join([f"<li>ID: {sol.get('id', 'N/A')} - Problem: {sol.get('problem_description', 'N/A')} <a href='/kb/solution/edit/{sol.get('id')}'>Edit</a> | <a href='/kb/solution/delete/{sol.get('id')}'>Delete</a></li>" for sol in solutions_data])
    except Exception as e: logger.error(f"Error loading solutions for KB management: {e}")

    content = f"""
    <h1>Knowledge Base Management</h1>
    <h2>FAQs (<a href="/kb/faq/add">Add New FAQ</a>)</h2>
    <ul>{faqs_html_list}</ul>
    <h2>Solutions (<a href="/kb/solution/add">Add New Solution</a>)</h2>
    <ul>{solutions_html_list}</ul>
    """
    return _render_base_template("KB Management", content, _get_nav_links_html())

def add_faq_page(): # Conceptual GET
    if not mock_session.get('logged_in_user'): return _render_base_template("Access Denied", "<h2>Access Denied</h2>", _get_nav_links_html())
    logger.info("Serving Add New FAQ page (Placeholder).")
    content = "<h2>Add New FAQ (Placeholder)</h2><form><!-- FAQ fields --><input type='submit' value='Save FAQ'></form><p><a href='/kb_management'>Back</a></p>"
    return _render_base_template("Add FAQ", content, _get_nav_links_html())

def add_solution_page(): # Conceptual GET
    if not mock_session.get('logged_in_user'): return _render_base_template("Access Denied", "<h2>Access Denied</h2>", _get_nav_links_html())
    logger.info("Serving Add New Solution page (Placeholder).")
    content = "<h2>Add New Solution (Placeholder)</h2><form><!-- Solution fields --><input type='submit' value='Save Solution'></form><p><a href='/kb_management'>Back</a></p>"
    return _render_base_template("Add Solution", content, _get_nav_links_html())

def edit_faq_page(faq_id): # Conceptual GET
    if not mock_session.get('logged_in_user'): return _render_base_template("Access Denied", "<h2>Access Denied</h2>", _get_nav_links_html())
    logger.info(f"Serving Edit FAQ page for ID: {faq_id} (Placeholder).")
    content = f"<h2>Edit FAQ: {faq_id} (Placeholder)</h2><form><!-- FAQ fields pre-filled --><input type='submit' value='Update FAQ'></form><p><a href='/kb_management'>Back</a></p>"
    return _render_base_template(f"Edit FAQ {faq_id}", content, _get_nav_links_html())

def edit_solution_page(solution_id): # Conceptual GET
    if not mock_session.get('logged_in_user'): return _render_base_template("Access Denied", "<h2>Access Denied</h2>", _get_nav_links_html())
    logger.info(f"Serving Edit Solution page for ID: {solution_id} (Placeholder).")
    content = f"<h2>Edit Solution: {solution_id} (Placeholder)</h2><form><!-- Solution fields pre-filled --><input type='submit' value='Update Solution'></form><p><a href='/kb_management'>Back</a></p>"
    return _render_base_template(f"Edit Solution {solution_id}", content, _get_nav_links_html())

def handle_save_item(item_type, form_data): # Conceptual POST
    if not mock_session.get('logged_in_user'): return {"status": "error", "message": "Access Denied."}
    logger.info(f"Attempting to save {item_type} with data: {form_data} (Conceptual - data not actually saved).")
    # In real app: load YAML, find item or add new, validate, dump YAML.
    return {"status": "success", "message": f"{item_type} conceptually saved."}

def handle_delete_item(item_type, item_id): # Conceptual POST/GET
    if not mock_session.get('logged_in_user'): return {"status": "error", "message": "Access Denied."}
    logger.info(f"Attempting to delete {item_type} with ID: {item_id} (Conceptual - data not actually deleted).")
    # In real app: load YAML, find and remove item, dump YAML.
    return {"status": "success", "message": f"{item_type} {item_id} conceptually deleted."}


# --- Placeholder execution for testing ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Simulating Admin Portal App Direct Script Run with Auth & KB Flow ---")

    os.makedirs(os.path.join(PROJECT_ROOT, "logs"), exist_ok=True)
    os.makedirs(UPLOAD_DIR_FOR_STT, exist_ok=True)
    os.makedirs(KB_BASE_PATH, exist_ok=True) # Ensure KB directory exists

    # Create dummy KB files for testing
    sample_faqs_content = """
faqs:
  - id: faq_billing_due_date
    intent: get_billing_info
    question_variants: ["When is my bill due?"]
    answer: "Your bill is due on the 15th."
  - id: faq_internet_plans
    intent: get_service_info
    question_variants: ["What internet plans?"]
    answer: "We have Basic and Premium."
"""
    sample_solutions_content = """
solutions:
  - id: sol_internet_no_connection
    problem_description: "No internet connection"
    steps: [{text: "Restart modem."}]
"""
    with open(FAQS_FILE_PATH, "w") as f: f.write(sample_faqs_content)
    with open(SOLUTIONS_FILE_PATH, "w") as f: f.write(sample_solutions_content)
    logger.info(f"Created dummy KB files in {KB_BASE_PATH}")

    # Simulate login
    handle_login("admin", "password123")
    logger.info(f"Current session state after login: {mock_session}")

    # Access KB Management Page
    logger.info("\n--- Accessing KB Management Page (Conceptual GET) ---")
    kb_page_html = kb_management_page()
    logger.info("KB Management page HTML generated (first 200 chars): " + kb_page_html.replace('\n',' ').strip()[:200] + "...")

    # Conceptual calls to add/edit/delete placeholders
    logger.info("\n--- Simulating KB Add/Edit/Delete Operations (Conceptual) ---")
    logger.info(f"Add FAQ Page: {add_faq_page()[:100]}...")
    logger.info(f"Save FAQ: {handle_save_item('FAQ', {'id': 'new_faq', 'question': 'New Q'})}")
    logger.info(f"Edit FAQ Page (faq_billing_due_date): {edit_faq_page('faq_billing_due_date')[:100]}...")
    logger.info(f"Delete FAQ (faq_internet_plans): {handle_delete_item('FAQ', 'faq_internet_plans')}")

    logger.info("\n--- Admin Portal App KB Flow Simulation Finished ---")
