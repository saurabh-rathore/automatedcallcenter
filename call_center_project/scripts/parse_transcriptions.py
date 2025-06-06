import os
import re
import logging
import argparse
import json
from datetime import datetime

# Setup logging
logger = logging.getLogger("TranscriptParser")
# Default logging setup, can be overridden by CLI args if called from another script that sets up logging.
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Regex to capture speaker turns and optional timestamps
# Example lines:
# Agent: Hello, how can I help you?
# [00:00:12.345] Customer: I have an issue.
# [00:00:15.120] Agent Smith: Yes, what is it?
# Unidentified Speaker: Some noise.
SPEAKER_PATTERN = re.compile(
    r"^(?:\[(\d{2}:\d{2}:\d{2}\.\d{3,})\]\s*)?"  # Optional timestamp: [HH:MM:SS.mmm]
    r"([\w\s]+?):"                             # Speaker name (e.g., "Agent", "Customer", "Agent Smith")
    r"\s*(.*)$"                                # Utterance
)

def parse_single_transcript(file_path):
    """
    Parses a single raw transcript file into a structured format.

    Args:
        file_path (str): Path to the raw transcript file.

    Returns:
        list: A list of dictionaries, where each dictionary represents an utterance
              with 'speaker', 'utterance', and optional 'timestamp' keys.
              Returns None if the file cannot be processed.
    """
    logger.info(f"Parsing transcript: {file_path}")
    parsed_utterances = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            current_speaker = None
            current_utterance_lines = []
            current_timestamp = None

            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line: # Skip empty lines
                    continue

                match = SPEAKER_PATTERN.match(line)
                if match:
                    # If there was a previous speaker, save their full utterance
                    if current_speaker and current_utterance_lines:
                        parsed_utterances.append({
                            "speaker": current_speaker,
                            "utterance": " ".join(current_utterance_lines).strip(),
                            "timestamp": current_timestamp
                        })
                        current_utterance_lines = []

                    # Start new utterance
                    current_timestamp = match.group(1) if match.group(1) else None # Optional timestamp
                    current_speaker = match.group(2).strip()
                    current_utterance_lines.append(match.group(3).strip())
                elif current_speaker:
                    # This line is a continuation of the previous speaker's utterance
                    current_utterance_lines.append(line)
                else:
                    # Line before any speaker identified, or malformed line
                    logger.warning(f"Line {line_num} in {file_path} without speaker identification: '{line}' (Skipping or treating as unknown)")
                    # Optionally, could assign to an "Unknown" speaker or prepend to next utterance.
                    # For now, if it's before any speaker, it's logged and skipped for structure.
                    # If it's after a speaker, it's appended.

            # Add the last utterance after EOF
            if current_speaker and current_utterance_lines:
                parsed_utterances.append({
                    "speaker": current_speaker,
                    "utterance": " ".join(current_utterance_lines).strip(),
                    "timestamp": current_timestamp
                })

        logger.info(f"Successfully parsed {len(parsed_utterances)} utterances from {file_path}")
        return parsed_utterances

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None
    except Exception as e:
        logger.exception(f"Error parsing file {file_path}: {e}")
        return None

def process_directory(input_dir, output_dir):
    """
    Processes all .txt files in the input directory and saves parsed JSON outputs
    to the output directory.
    """
    logger.info(f"Starting to process directory: {input_dir}")
    os.makedirs(output_dir, exist_ok=True)

    processed_count = 0
    failed_count = 0

    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"): # Assuming raw transcripts are .txt files
            raw_file_path = os.path.join(input_dir, filename)
            logger.info(f"Processing raw transcript: {raw_file_path}")

            parsed_data = parse_single_transcript(raw_file_path)

            if parsed_data:
                output_filename = os.path.splitext(filename)[0] + ".json"
                output_file_path = os.path.join(output_dir, output_filename)
                try:
                    with open(output_file_path, 'w', encoding='utf-8') as f_out:
                        json.dump(parsed_data, f_out, indent=4)
                    logger.info(f"Saved parsed transcript to: {output_file_path}")
                    processed_count += 1
                except Exception as e:
                    logger.exception(f"Error saving parsed data for {filename} to JSON: {e}")
                    failed_count += 1
            else:
                logger.warning(f"Skipping file {filename} due to parsing errors or empty content.")
                failed_count += 1
        else:
            logger.debug(f"Skipping non-txt file: {filename}")

    logger.info(f"--- Processing Summary ---")
    logger.info(f"Successfully processed and saved: {processed_count} files.")
    logger.info(f"Failed to process or skipped: {failed_count} files.")
    logger.info(f"Parsed files are located in: {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse raw call center transcriptions into a structured JSON format.")

    # Define project root relative to this script's location (scripts/)
    project_root_for_defaults = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    default_input_path = os.path.join(project_root_for_defaults, "data", "raw_transcripts")
    default_output_path = os.path.join(project_root_for_defaults, "data", "parsed_transcripts")

    parser.add_argument("--input-dir", type=str, default=default_input_path,
                        help="Directory containing raw transcript files (default: data/raw_transcripts).")
    parser.add_argument("--output-dir", type=str, default=default_output_path,
                        help="Directory where parsed JSON files will be saved (default: data/parsed_transcripts).")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level (default: INFO).")

    args = parser.parse_args()

    # Reconfigure logger based on CLI arguments if needed (or rely on basicConfig if simple)
    # For more control, you might set up handlers as in retrain_orchestrator.py
    logger.setLevel(args.log_level.upper())
    # If you want file logging for this script specifically:
    # file_handler = logging.FileHandler(os.path.join(project_root_for_defaults, "logs", "parse_transcriptions.log"))
    # file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    # logger.addHandler(file_handler)

    logger.info(f"Starting transcript parsing process with input: '{args.input_dir}', output: '{args.output_dir}'")
    process_directory(args.input_dir, args.output_dir)
    logger.info("Transcript parsing process finished.")
