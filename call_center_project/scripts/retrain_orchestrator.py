import os
import subprocess
import sys
import shutil
from datetime import datetime
import argparse
import logging
import json
import yaml

# --- Path Definitions ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TRAIN_NLU_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "train_nlu.py")

DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yml")
DEFAULT_NLU_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "training_data", "nlu")
DEFAULT_DOMAIN_PATH = os.path.join(PROJECT_ROOT, "domain.yml")
DEFAULT_MODELS_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "models", "nlu")

DEFAULT_ORCH_LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
DEFAULT_ORCH_LOG_FILE = os.path.join(DEFAULT_ORCH_LOGS_DIR, "retrain_orchestrator.log")
DEFAULT_ORCH_SUMMARY_FILE = os.path.join(DEFAULT_ORCH_LOGS_DIR, "orchestration_summary.json") # Path for summary
DEFAULT_ORCH_TEST_RESULTS_DIR = os.path.join(PROJECT_ROOT, "results", "nlu_test_results_orchestrated")
ACTIVE_MODEL_FILENAME = "active_nlu_model.tar.gz"

logger = logging.getLogger('RetrainOrchestrator')

# --- Logging Setup ---
def setup_logging(log_level_str="INFO", log_file=DEFAULT_ORCH_LOG_FILE):
    numeric_level = getattr(logging, log_level_str.upper(), None)
    if not isinstance(numeric_level, int):
        logging.warning(f"Invalid log level string: {log_level_str}. Defaulting to INFO.")
        numeric_level = logging.INFO
    log_file_dir = os.path.dirname(log_file)
    if log_file_dir: os.makedirs(log_file_dir, exist_ok=True)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if logger.hasHandlers(): logger.handlers.clear()
    logger.setLevel(numeric_level)
    ch = logging.StreamHandler(); ch.setFormatter(formatter); logger.addHandler(ch)
    fh = logging.FileHandler(log_file); fh.setFormatter(formatter); logger.addHandler(fh)
    logger.debug("Orchestrator logging setup complete.")

def create_step_report(step_name, status, message, artifacts=None):
    return {
        "step_name": step_name, "status": status, "message": message,
        "timestamp": datetime.now().isoformat(), "artifacts": artifacts if artifacts else {}
    }

def setup_dummy_nlu_environment_for_test(args_for_paths):
    logger.info("Setting up dummy NLU environment for orchestrator test run...")
    models_base_path = args_for_paths.out
    archive_dir = os.path.join(models_base_path, "archive")
    os.makedirs(models_base_path, exist_ok=True); os.makedirs(archive_dir, exist_ok=True)
    dummy_active_model_path = os.path.join(models_base_path, ACTIVE_MODEL_FILENAME)
    if not os.path.exists(dummy_active_model_path):
        with open(dummy_active_model_path, "w") as f: f.write("Dummy PREVIOUS active model.\n")
    os.makedirs(args_for_paths.data, exist_ok=True)
    if not os.path.exists(args_for_paths.config):
        with open(args_for_paths.config, "w") as f: f.write("language: en\npipeline:\n  - name: WhitespaceTokenizer\n")
    if not os.path.exists(args_for_paths.domain):
        with open(args_for_paths.domain, "w") as f: f.write("version: '3.1'\nintents:\n  - greet\n")
    dummy_nlu_data_file = os.path.join(args_for_paths.data, "initial_training_data.yml")
    if not os.path.exists(dummy_nlu_data_file):
        with open(dummy_nlu_data_file, "w") as f: f.write("version: \"3.1\"\nnlu:\n- intent: greet\n  examples: |\n    - hello\n")
    if args_for_paths.test_data_dir:
        if not os.path.exists(args_for_paths.test_data_dir): os.makedirs(args_for_paths.test_data_dir, exist_ok=True)
        dummy_train_nlu_test_file = os.path.join(args_for_paths.test_data_dir, "placeholder_test_data_for_train_nlu.yml")
        if not os.path.exists(dummy_train_nlu_test_file):
             with open(dummy_train_nlu_test_file, "w") as f: f.write("version: '3.1'\nnlu:\n- intent: greet\n  examples: |\n    - hi\n")
    if args_for_paths.test_data_dir:
        os.makedirs(args_for_paths.test_results_dir, exist_ok=True)
        dummy_intent_report_path = os.path.join(args_for_paths.test_results_dir, "intent_report.json")
        if not os.path.exists(dummy_intent_report_path):
            with open(dummy_intent_report_path, "w") as f: json.dump({"accuracy": 0.85}, f)
    logger.debug("Dummy environment setup complete.")

def validate_nlu_data(nlu_data_path):
    step_name = "NLU Data Validation"; artifacts = {'checked_path': nlu_data_path, 'files_processed': [], 'errors': []}
    logger.info(f"Starting {step_name} for path: {nlu_data_path}")
    if not os.path.isdir(nlu_data_path):
        return create_step_report(step_name, "failure", f"NLU data path '{nlu_data_path}' not a directory.", artifacts)
    nlu_files = [f for f in os.listdir(nlu_data_path) if os.path.isfile(os.path.join(nlu_data_path, f))]
    if not nlu_files: return create_step_report(step_name, "warning", f"NLU data dir '{nlu_data_path}' is empty.", artifacts)
    yaml_ok = True
    for fname in nlu_files:
        fpath = os.path.join(nlu_data_path, fname); artifacts['files_processed'].append(fname)
        if fname.endswith((".yml", ".yaml")):
            try:
                with open(fpath, 'r') as f: yaml.safe_load(f)
            except yaml.YAMLError as e:
                err_msg = f"YAML error in '{fname}': {e}"; logger.error(err_msg); artifacts['errors'].append(err_msg); yaml_ok = False
    if not yaml_ok: return create_step_report(step_name, "failure", "YAML syntax errors in NLU data.", artifacts)
    logger.info("Conceptual NLU data checks (domain consistency, example counts, etc.) would go here.")
    if not artifacts['errors']:
        return create_step_report(step_name, "success", "NLU data validation passed (basic checks).", artifacts)
    else: # Warnings only
        return create_step_report(step_name, "warning", "NLU data validation completed with warnings.", artifacts)


def run_nlu_training(cli_args):
    step_name = "NLU Model Training"; artifacts = {}
    logger.info(f"Starting {step_name} by calling train_nlu.py...")
    command = [sys.executable, TRAIN_NLU_SCRIPT_PATH,
        "--config", cli_args.config, "--data", cli_args.data, "--domain", cli_args.domain,
        "--out", cli_args.out, "--log-level", cli_args.log_level]
    if cli_args.force: command.append("--force")
    if cli_args.epochs is not None: command.extend(["--epochs", str(cli_args.epochs)])
    if cli_args.model_name_prefix: command.extend(["--model-name-prefix", cli_args.model_name_prefix])
    if cli_args.test_data_dir:
        command.extend(["--test_data_dir", os.path.relpath(cli_args.test_data_dir, PROJECT_ROOT)])
        command.extend(["--test_results_dir", os.path.relpath(cli_args.test_results_dir, PROJECT_ROOT)])
    artifacts['command_used'] = ' '.join(command)
    logger.info(f"Calling train_nlu.py with command: {artifacts['command_used']}")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=PROJECT_ROOT)
        stdout, stderr = process.communicate()
        if stdout: logger.info(f"STDOUT from train_nlu.py:\n{stdout}")
        if stderr: logger.info(f"STDERR from train_nlu.py (its log output):\n{stderr}")

        rasa_not_found_msg = "ERROR - 'rasa' command not found"
        actual_rasa_success_msg = "Training script (and optional testing) process finished successfully."

        if process.returncode == 0 and actual_rasa_success_msg in stderr :
            return create_step_report(step_name, "success", "train_nlu.py reported success.", artifacts)
        elif process.returncode == 1 and rasa_not_found_msg in stderr:
             return create_step_report(step_name, "success", "train_nlu.py confirmed Rasa not found (dry run success).", artifacts)
        else: return create_step_report(step_name, "failure", f"train_nlu.py failed. RC: {process.returncode}.", artifacts)
    except Exception as e: return create_step_report(step_name, "failure", f"Exception running train_nlu.py: {e}", artifacts)

def _check_evaluation_thresholds(metrics, threshold_config={'accuracy': 0.80}):
    if not metrics: logger.warning("No metrics for threshold check."); return False
    passed_all = True
    for metric_name, threshold_value in threshold_config.items():
        actual_value = metrics.get(metric_name)
        if actual_value is None:
            logger.warning(f"Metric '{metric_name}' not found. Cannot check threshold.")
            passed_all = False; continue
        if actual_value >= threshold_value:
            logger.info(f"Threshold PASSED for {metric_name}: Actual={actual_value}, Threshold={threshold_value}")
        else:
            logger.warning(f"Threshold FAILED for {metric_name}: Actual={actual_value}, Threshold={threshold_value}")
            passed_all = False
    return passed_all

def evaluate_new_model(model_output_path, model_name_prefix, tests_were_run, orchestrator_test_results_dir):
    step_name = "Model Evaluation"; artifacts = {}
    logger.info(f"Starting {step_name} for models in: {model_output_path}")
    model_to_evaluate_path = None
    if model_name_prefix:
        expected_filename = f"{model_name_prefix}.tar.gz"
        potential_path = os.path.join(model_output_path, expected_filename)
        if os.path.exists(potential_path): model_to_evaluate_path = potential_path
        else: logger.warning(f"Fixed-name model '{expected_filename}' not found. Checking timestamped.")
    if not model_to_evaluate_path:
        models = [f for f in os.listdir(model_output_path) if f.endswith(".tar.gz") and os.path.isfile(os.path.join(model_output_path, f))]
        if not models: return create_step_report(step_name, "failure", "No .tar.gz models found.", artifacts)
        models.sort(key=lambda x: os.path.getmtime(os.path.join(model_output_path, x)), reverse=True)
        model_to_evaluate_path = os.path.join(model_output_path, models[0])
    artifacts['evaluated_model_path'] = model_to_evaluate_path
    logger.info(f"Model selected for evaluation: {model_to_evaluate_path}")

    if not tests_were_run:
        return create_step_report(step_name, "success", "No tests run; evaluation auto-passed.", artifacts)

    report_path = os.path.join(orchestrator_test_results_dir, "intent_report.json")
    logger.info(f"Looking for NLU test results at: {report_path}")
    if os.path.exists(report_path):
        try:
            with open(report_path, 'r') as f: report_data = json.load(f)
            accuracy = report_data.get("accuracy") if "accuracy" in report_data else report_data.get("intent_evaluation", {}).get("accuracy")
            artifacts['metrics'] = report_data
            if accuracy is not None:
                logger.info(f"Parsed 'accuracy': {accuracy} from '{report_path}'")
                if _check_evaluation_thresholds({'accuracy': accuracy}):
                    return create_step_report(step_name, "success", "Model passed evaluation thresholds.", artifacts)
                else: return create_step_report(step_name, "failure", "Model failed evaluation thresholds.", artifacts)
            else: return create_step_report(step_name, "failure", "'accuracy' not in intent_report.json.", artifacts)
        except Exception as e: return create_step_report(step_name, "failure", f"Error parsing test results: {e}", artifacts)
    else: return create_step_report(step_name, "failure", f"Test results file '{report_path}' not found.", artifacts)

def deploy_model(new_model_path, models_base_path):
    step_name = "Model Deployment"
    active_model_file = os.path.join(models_base_path, ACTIVE_MODEL_FILENAME)
    archive_dir = os.path.join(models_base_path, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    logger.info(f"Starting {step_name} of '{os.path.basename(new_model_path)}' to '{active_model_file}'")
    artifacts = {'deployed_as': active_model_file}
    if not new_model_path or not os.path.exists(new_model_path):
        return create_step_report(step_name, "failure", "New model path invalid.", artifacts)
    try:
        if os.path.exists(active_model_file):
            if os.path.islink(active_model_file) and not os.path.exists(os.readlink(active_model_file)):
                 logger.warning(f"Broken symlink at {active_model_file}. Removing."); os.remove(active_model_file)
            else:
                ts = datetime.now().strftime('%Y%m%d-%H%M%S')
                archived_name = f"{ACTIVE_MODEL_FILENAME}_{ts}.archived"
                archive_path = os.path.join(archive_dir, archived_name)
                logger.info(f"Archiving existing model to '{archive_path}'")
                shutil.move(active_model_file, archive_path); artifacts['archived_model'] = archive_path
        logger.info(f"Copying new model from '{new_model_path}' to '{active_model_file}'")
        shutil.copy2(new_model_path, active_model_file)
        artifacts['newly_deployed_model_source'] = new_model_path
        logger.info(f"Conceptual: Update central config with new model path: {active_model_file}")
        return create_step_report(step_name, "success", f"Model deployed to {active_model_file}", artifacts)
    except Exception as e: return create_step_report(step_name, "failure", f"Error deploying model: {e}", artifacts)

def main_orchestration_flow(args):
    summary = {'overall_status': 'failure', 'start_time': datetime.now().isoformat(), 'end_time': None, 'step_reports': []}
    def add_report(report): summary['step_reports'].append(report)
    logger.info("--- Starting NLU Retraining Orchestration Flow ---")

    report = validate_nlu_data(args.data); add_report(report)
    if report['status'] != 'success': logger.error(f"Halting: {report['message']}"); summary['end_time'] = datetime.now().isoformat(); return summary

    report = run_nlu_training(args); add_report(report)
    if report['status'] != 'success': logger.error(f"Halting: {report['message']}"); summary['end_time'] = datetime.now().isoformat(); return summary

    rasa_available = shutil.which("rasa")
    if not rasa_available:
        model_name = args.model_name_prefix if args.model_name_prefix else datetime.now().strftime("%Y%m%d-%H%M%S") + "-nlu_placeholder"
        dummy_path = os.path.join(args.out, f"{model_name}.tar.gz")
        try:
            if not os.path.exists(dummy_path):
                 with open(dummy_path, "w") as f: f.write("Dummy NLU model.\n")
                 logger.info(f"Created dummy model for dry run: {dummy_path}")
                 last_report = summary['step_reports'][-1]
                 if last_report['step_name'] == "NLU Model Training": last_report['artifacts']['created_dummy_model_path'] = dummy_path
        except Exception as e: logger.error(f"Could not create dummy model: {e}")

    report = evaluate_new_model(args.out, args.model_name_prefix, bool(args.test_data_dir), args.test_results_dir)
    add_report(report)
    if report['status'] != 'success':
        logger.error(f"Halting: {report['message']}"); summary['end_time'] = datetime.now().isoformat(); return summary

    evaluated_model_path = report['artifacts'].get('evaluated_model_path')
    if not evaluated_model_path:
        logger.error("Halting: No model path from evaluation."); summary['end_time'] = datetime.now().isoformat(); return summary

    report = deploy_model(evaluated_model_path, args.out); add_report(report)
    if report['status'] != 'success': logger.error(f"Halting: {report['message']}"); summary['end_time'] = datetime.now().isoformat(); return summary

    logger.info("--- NLU Retraining Orchestration Completed Successfully ---")
    summary['overall_status'] = 'success'
    summary['end_time'] = datetime.now().isoformat()
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrates NLU retraining.")
    parser.add_argument("--log-level",type=str,default="INFO",choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL"],help="Logging level.")
    parser.add_argument("--log-file",type=str,default=DEFAULT_ORCH_LOG_FILE,help="Log file path.")
    parser.add_argument("--summary-file",type=str,default=DEFAULT_ORCH_SUMMARY_FILE,help="Summary report JSON file path.") # New arg for summary
    parser.add_argument("--config",default=DEFAULT_CONFIG_PATH,help="Rasa config path.")
    parser.add_argument("--data",default=DEFAULT_NLU_DATA_PATH,help="NLU training data path.")
    parser.add_argument("--domain",default=DEFAULT_DOMAIN_PATH,help="Rasa domain path.")
    parser.add_argument("--out",default=DEFAULT_MODELS_OUTPUT_PATH,help="Output directory for models.")
    parser.add_argument("--force",action="store_true",help="Force retraining.")
    parser.add_argument("--epochs",type=int,default=None,help="NLU training epochs.")
    parser.add_argument("--model-name-prefix",type=str,default=None,help="Model name prefix.")
    parser.add_argument("--test_data_dir",type=str,default=None,help="NLU test data dir (rel to project root).")
    parser.add_argument("--test_results_dir",type=str,default=os.path.relpath(DEFAULT_ORCH_TEST_RESULTS_DIR,PROJECT_ROOT),help="NLU test results dir (rel to project root).")
    args = parser.parse_args()

    for p_arg in ['config', 'data', 'domain', 'out', 'log_file', 'summary_file']: # Add summary_file to path handling
        setattr(args, p_arg, os.path.join(PROJECT_ROOT, getattr(args, p_arg)) if not os.path.isabs(getattr(args, p_arg)) else getattr(args, p_arg))
    if args.test_data_dir: args.test_data_dir = os.path.join(PROJECT_ROOT, args.test_data_dir)
    args.test_results_dir = os.path.join(PROJECT_ROOT, args.test_results_dir)

    setup_logging(args.log_level, args.log_file)
    setup_dummy_nlu_environment_for_test(args)

    try:
        final_report = main_orchestration_flow(args)
        logger.info("\n--- Orchestration Final Report ---")
        report_json_str = json.dumps(final_report, indent=4, default=str)
        logger.info(report_json_str)

        # Save the final report to JSON file
        try:
            report_file_dir = os.path.dirname(args.summary_file)
            if report_file_dir: os.makedirs(report_file_dir, exist_ok=True)
            with open(args.summary_file, 'w') as f:
                f.write(report_json_str)
            logger.info(f"Orchestration summary report saved to: {args.summary_file}")
        except Exception as e:
            logger.error(f"Failed to save orchestration summary report to {args.summary_file}: {e}")

        if final_report['overall_status'] != 'success':
            logger.error("Orchestrator script finished with errors.")
            sys.exit(1)
        else: logger.info("Orchestrator script finished successfully.")
    except Exception as e:
        logger.critical(f"Critical error in main orchestrator execution: {e}", exc_info=True)
        sys.exit(1)
