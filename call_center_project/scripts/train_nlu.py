import subprocess
import os
import argparse
from datetime import datetime
import sys
import shutil
import logging

# Define default paths relative to the project root (call_center_project)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
DEFAULT_LOG_FILE_PATH = os.path.join(DEFAULT_LOGS_DIR, "nlu_training.log")
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yml")
DEFAULT_NLU_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "training_data", "nlu")
DEFAULT_MODELS_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "models", "nlu")
DEFAULT_DOMAIN_PATH = os.path.join(PROJECT_ROOT, "domain.yml")
DEFAULT_TEST_RESULTS_DIR = os.path.join(PROJECT_ROOT, "results", "nlu_test_results")

# Setup a specific logger for this script
logger = logging.getLogger('NluTrainingScript')

def setup_logging(log_level_str="INFO", log_file=DEFAULT_LOG_FILE_PATH):
    numeric_level = getattr(logging, log_level_str.upper(), None)
    if not isinstance(numeric_level, int):
        # Fallback to INFO if invalid level string is provided, and log a warning.
        logging.warning(f"Invalid log level string: {log_level_str}. Defaulting to INFO.")
        numeric_level = logging.INFO

    log_file_dir = os.path.dirname(log_file)
    if log_file_dir:
        os.makedirs(log_file_dir, exist_ok=True)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Check if handlers are already present to avoid duplication if script is re-run in same session
    if not logger.handlers:
        logger.setLevel(numeric_level) # Set level on the logger itself

        # Console Handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File Handler
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    else: # If handlers exist, just ensure the level is set
        logger.setLevel(numeric_level)
        for handler in logger.handlers: # Optionally update handler levels too if needed
            handler.setLevel(numeric_level)

    logger.debug("Logging setup complete.")


def log_subprocess_output(process, phase_name):
    stdout_lines = []
    stderr_lines = []

    logger.info(f"--- {phase_name} STDOUT ---")
    for line in iter(process.stdout.readline, ''):
        stripped_line = line.strip()
        logger.info(stripped_line)
        stdout_lines.append(stripped_line)
    process.stdout.close()
    logger.info(f"--- End of {phase_name} STDOUT ---")

    stderr_output = process.stderr.read()
    process.stderr.close()
    if stderr_output:
        logger.warning(f"--- {phase_name} STDERR ---")
        for line in stderr_output.strip().split('\n'):
            logger.warning(line)
            stderr_lines.append(line)
        logger.warning(f"--- End of {phase_name} STDERR ---")
    else:
        logger.info(f"--- {phase_name} STDERR was empty ---")

    return stdout_lines, stderr_lines

def train_rasa_nlu_model(
    config_path=DEFAULT_CONFIG_PATH,
    nlu_data_path=DEFAULT_NLU_DATA_PATH,
    domain_path=DEFAULT_DOMAIN_PATH,
    models_output_path=DEFAULT_MODELS_OUTPUT_PATH,
    force_training=False,
    epochs=None,
    model_name_prefix=None, # New argument
    test_data_dir=None,
    test_results_dir=DEFAULT_TEST_RESULTS_DIR
):
    logger.info("--- Starting Rasa NLU Model Processing ---")
    logger.info(f"Project Root: {PROJECT_ROOT}")
    logger.info(f"Using Config: {config_path}")
    logger.info(f"Using NLU Data from: {nlu_data_path}")
    logger.info(f"Using Domain from: {domain_path}")
    logger.info(f"Models will be saved to: {models_output_path}")
    if epochs is not None:
        logger.info(f"Custom Epochs: {epochs}")
    if model_name_prefix:
        logger.info(f"Model Name Prefix: {model_name_prefix}")
    if force_training:
        logger.info("Force training enabled.")
    if test_data_dir:
        logger.info(f"NLU Test Data from: {test_data_dir}")
        logger.info(f"NLU Test Results will be saved to: {test_results_dir}")

    if not all(os.path.exists(p) for p in [config_path, domain_path]):
        logger.error(f"Config file ({config_path}) or Domain file ({domain_path}) not found.")
        return False
    if not os.path.exists(nlu_data_path) or not os.listdir(nlu_data_path):
        logger.error(f"NLU training data directory not found or empty at {nlu_data_path}")
        return False

    os.makedirs(models_output_path, exist_ok=True)

    rasa_executable = shutil.which("rasa")
    if not rasa_executable:
        logger.error("'rasa' command not found or not executable. Please ensure Rasa is installed and in PATH.")
        return False
    logger.info(f"Found Rasa executable at: {rasa_executable}")

    logger.info("--- Phase 1: NLU Model Training ---")
    rasa_train_command = [
        rasa_executable, "train", "nlu",
        "--config", config_path,
        "--nlu", nlu_data_path,
        "--domain", domain_path,
        "--out", models_output_path
    ]
    if force_training:
        rasa_train_command.append("--force")
    if epochs is not None:
        rasa_train_command.extend(["--epochs", str(epochs)])
    if model_name_prefix:
        rasa_train_command.extend(["--fixed-model-name", model_name_prefix])

    training_successful = False
    latest_model_file_path = None

    try:
        logger.info(f"Executing Rasa training command: {' '.join(rasa_train_command)}")
        process_train = subprocess.Popen(rasa_train_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=PROJECT_ROOT)
        train_stdout_lines, train_stderr_lines = log_subprocess_output(process_train, "Rasa Training")
        rc_train = process_train.wait()

        if rc_train == 0:
            logger.info("Rasa NLU model training process completed with return code 0.")
            rasa_success_indicators = ["NLU model training completed.", "Your Rasa model is trained"]
            if any(indicator in line for line in train_stdout_lines for indicator in rasa_success_indicators):
                logger.info("Rasa NLU model training reported successful completion based on output.")

                if model_name_prefix:
                    fixed_model_name = f"{model_name_prefix}.tar.gz"
                    potential_model_path = os.path.join(models_output_path, fixed_model_name)
                    if os.path.exists(potential_model_path):
                        latest_model_file_path = potential_model_path
                        logger.info(f"Trained model saved as (fixed name): {latest_model_file_path}")
                    else:
                        logger.warning(f"Rasa training reported success, but fixed model name '{fixed_model_name}' not found in '{models_output_path}'. Listing timestamped models if any.")
                        # Fallback to finding latest timestamped if fixed name isn't there
                        trained_models_list = sorted([f for f in os.listdir(models_output_path) if f.endswith(".tar.gz")], key=lambda x: os.path.getmtime(os.path.join(models_output_path, x)), reverse=True)
                        if trained_models_list:
                            latest_model_file_path = os.path.join(models_output_path, trained_models_list[0])
                            logger.info(f"Latest model (timestamped): {latest_model_file_path}")
                        else:
                            logger.error("No .tar.gz model files found in output directory despite successful Rasa report.")
                else: # No prefix, find latest timestamped
                    trained_models_list = sorted([f for f in os.listdir(models_output_path) if f.endswith(".tar.gz")], key=lambda x: os.path.getmtime(os.path.join(models_output_path, x)), reverse=True)
                    if trained_models_list:
                        latest_model_file_path = os.path.join(models_output_path, trained_models_list[0])
                        logger.info(f"Latest model (timestamped): {latest_model_file_path}")
                    else:
                        logger.error("No .tar.gz model files found in output directory despite successful Rasa report.")

                if train_stderr_lines:
                    logger.warning("Output detected on stderr during successful training (rc=0). Review details above.")
                training_successful = True # Mark as successful if Rasa reported success.
            else:
                logger.error("Rasa training process (train nlu) exited with 0, but expected success indicators not found in STDOUT.")
        else:
            logger.error(f"Rasa NLU training process failed with return code: {rc_train}. Review STDOUT/STDERR above.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during training execution: {e}")
        return False

    if not training_successful or not latest_model_file_path: # Ensure a model path was actually identified
        logger.error("Training phase did not result in a usable model file.")
        return False

    if test_data_dir:
        logger.info("--- Phase 2: NLU Model Evaluation ---")
        abs_test_data_dir = os.path.join(PROJECT_ROOT, test_data_dir)
        abs_test_results_dir = os.path.join(PROJECT_ROOT, test_results_dir)

        if not os.path.exists(abs_test_data_dir) or not os.listdir(abs_test_data_dir):
            logger.warning(f"NLU test data directory '{abs_test_data_dir}' not found or empty. Skipping evaluation.")
        else:
            os.makedirs(abs_test_results_dir, exist_ok=True)
            logger.info(f"NLU test results will be saved to: {abs_test_results_dir}")
            rasa_test_command = [
                rasa_executable, "test", "nlu",
                "--model", latest_model_file_path,
                "--data", abs_test_data_dir,
                "--out", abs_test_results_dir]
            try:
                logger.info(f"Executing Rasa test command: {' '.join(rasa_test_command)}")
                process_test = subprocess.Popen(rasa_test_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=PROJECT_ROOT)
                _ , test_stderr_lines = log_subprocess_output(process_test, "Rasa Testing") # Stdout of test is usually large
                rc_test = process_test.wait()
                if rc_test == 0:
                    logger.info("Rasa NLU model testing process completed successfully (rc=0).")
                    if test_stderr_lines:
                         logger.warning("Output detected on stderr during successful testing (rc=0). Review details above.")
                else:
                    logger.error(f"Rasa NLU model testing process failed with return code: {rc_test}. Review STDOUT/STDERR above.")
            except Exception as e:
                logger.exception(f"An unexpected error occurred during testing execution: {e}")
    else:
        logger.info("NLU test data directory not provided (or Rasa not found for training). Skipping automatic evaluation.")

    return training_successful

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train and optionally test Rasa NLU model.")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level.")
    parser.add_argument("--log-file", type=str, default=DEFAULT_LOG_FILE_PATH, help=f"Path to log file.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to Rasa config file.")
    parser.add_argument("--data", default=DEFAULT_NLU_DATA_PATH, help="Path to NLU training data directory.")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN_PATH, help="Path to Rasa domain file.")
    parser.add_argument("--out", default=DEFAULT_MODELS_OUTPUT_PATH, help="Directory to save trained models.")
    parser.add_argument("--force", action="store_true", help="Force Rasa to retrain even if data hasn't ostensibly changed.")
    parser.add_argument("--epochs", type=int, default=None, help="Number of epochs for NLU components.")
    parser.add_argument("--model-name-prefix", type=str, default=None, help="Custom prefix for the trained model name. Results in '<prefix>.tar.gz'.")
    parser.add_argument("--test_data_dir", type=str, default=None, help="Path to NLU test data directory (relative to project root).")
    parser.add_argument("--test_results_dir", type=str, default=os.path.relpath(DEFAULT_TEST_RESULTS_DIR, PROJECT_ROOT), help="Directory to save NLU test results (relative to project root).")

    args = parser.parse_args()

    setup_logging(args.log_level, args.log_file)

    if args.test_data_dir:
        abs_cli_test_data_dir = os.path.join(PROJECT_ROOT, args.test_data_dir)
        if not os.path.exists(abs_cli_test_data_dir):
            logger.info(f"Creating dummy NLU test data directory for script execution: {abs_cli_test_data_dir}")
            os.makedirs(abs_cli_test_data_dir, exist_ok=True)
        dummy_test_file = os.path.join(abs_cli_test_data_dir, "placeholder_test_data.yml")
        if not os.path.exists(dummy_test_file):
             with open(dummy_test_file, "w") as f:
                 f.write("version: '3.1'\nnlu:\n- intent: greet\n  examples: |\n    - hi test example for CLI run\n")
             logger.info(f"Created dummy NLU test data file: {dummy_test_file}")
        args.test_data_dir = abs_cli_test_data_dir

    args.test_results_dir = os.path.join(PROJECT_ROOT, args.test_results_dir)

    try:
        success = train_rasa_nlu_model(
            config_path=args.config,
            nlu_data_path=args.data,
            domain_path=args.domain,
            models_output_path=args.out,
            force_training=args.force,
            epochs=args.epochs,
            model_name_prefix=args.model_name_prefix,
            test_data_dir=args.test_data_dir,
            test_results_dir=args.test_results_dir
        )
        if success:
            logger.info("Training script (and optional testing) process finished successfully.")
        else:
            logger.error("Training script (or optional testing) process encountered errors or Rasa not found.")
            sys.exit(1)
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}", exc_info=True)
        sys.exit(1)
