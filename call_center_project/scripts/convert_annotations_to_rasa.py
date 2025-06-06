import json
import yaml
import os
import argparse
import logging
from collections import defaultdict
from datetime import datetime

# Setup logging
logger = logging.getLogger("AnnotationConverter")
if not logger.handlers: # Setup basic config only if no handlers are present
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def convert_to_rasa_nlu_format(annotated_transcript_path):
    """
    Converts an annotated transcript (JSON from parsing + annotations) to Rasa NLU YAML format.

    Args:
        annotated_transcript_path (str): Path to the annotated transcript JSON file.

    Returns:
        dict: Rasa NLU compatible dictionary (or None if conversion fails).
              Structure: {"nlu": [{"intent": "intent_name", "examples": ["example1", "example with [entity](entity_type)"]}]}
    """
    logger.info(f"Converting annotated transcript: {annotated_transcript_path}")
    try:
        with open(annotated_transcript_path, 'r', encoding='utf-8') as f:
            annotated_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Annotated transcript file not found: {annotated_transcript_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {annotated_transcript_path}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error loading {annotated_transcript_path}: {e}")
        return None

    # Group examples by intent
    intent_examples = defaultdict(list)
    processed_utterances = 0

    for utterance_data in annotated_data:
        text = utterance_data.get("utterance")
        intent = utterance_data.get("intent") # Assuming intent is annotated at utterance level
        entities = utterance_data.get("entities", []) # Assuming entities are annotated

        if not text:
            logger.warning(f"Skipping utterance without text: {utterance_data}")
            continue

        # If intent is present, this utterance is a candidate for NLU data
        if intent:
            example_text = text # This is the working copy that will be modified if entities exist
            if entities:
                # Sort entities by start position in *ascending* order
                entities.sort(key=lambda x: x.get("start_char", 0))

                parts = []
                last_end = 0
                for entity in entities:
                    start = entity.get("start_char")
                    end = entity.get("end_char")
                    entity_type = entity.get("entity_type")

                    if None not in [start, end, entity_type]:
                        # Append text before the current entity
                        parts.append(text[last_end:start]) # Slices are from original 'text'

                        # Extract original entity text and create markup
                        entity_value_original_text = text[start:end] # Slices are from original 'text'
                        markup = f"[{entity_value_original_text}]({entity_type})"
                        parts.append(markup)

                        last_end = end
                    else:
                        logger.warning(f"Skipping entity with missing fields in '{text}': {entity}")

                # Append any remaining text after the last entity
                parts.append(text[last_end:])
                example_text = "".join(parts) # Reconstruct the text with markups

            intent_examples[intent].append(f"- {example_text}") # Rasa examples are list items
            processed_utterances += 1
        else:
            logger.debug(f"Skipping utterance without 'intent' annotation: '{text[:50]}...'")

    if not intent_examples:
        logger.info("No utterances with intent annotations found in the input file.")
        return {"version": "3.1", "nlu": []}

    rasa_nlu_data = []
    for intent_name, examples_list in intent_examples.items():
        rasa_nlu_data.append({
            "intent": intent_name,
            "examples": "\n".join(examples_list)
        })

    logger.info(f"Successfully converted {processed_utterances} utterances into Rasa NLU format.")
    return {"version": "3.1", "nlu": rasa_nlu_data}

def merge_nlu_data(existing_data, new_data):
    if not new_data or not new_data.get("nlu"):
        logger.info("New data is empty, nothing to merge.")
        return existing_data
    if not existing_data or not existing_data.get("nlu"):
        logger.info("Existing data is empty or invalid, using new data as base.")
        return new_data
    existing_intents_map = {item["intent"]: item for item in existing_data["nlu"]}
    for new_item in new_data["nlu"]:
        intent_name = new_item["intent"]
        new_examples_str = new_item["examples"]
        if intent_name in existing_intents_map:
            logger.info(f"Appending examples to existing intent: {intent_name}")
            existing_examples_str = existing_intents_map[intent_name].get("examples", "")
            if existing_examples_str:
                existing_intents_map[intent_name]["examples"] = existing_examples_str + "\n" + new_examples_str
            else:
                existing_intents_map[intent_name]["examples"] = new_examples_str
        else:
            logger.info(f"Adding new intent: {intent_name}")
            existing_data["nlu"].append(new_item)
    return existing_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert annotated transcripts to Rasa NLU YAML format.")
    project_root_for_defaults = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    default_output_nlu_file = os.path.join(project_root_for_defaults, "data", "training_data", "nlu", f"converted_nlu_data_{datetime.now().strftime('%Y%m%d%H%M%S')}.yml")
    parser.add_argument("input_file", type=str, help="Path to the annotated transcript JSON file.")
    parser.add_argument("--output-file", type=str, default=None, help=f"Path to save NLU YAML (default: data/training_data/nlu/converted_TIMESTAMP.yml).")
    parser.add_argument("--merge-with", type=str, default=None, help="Optional: Path to existing NLU YAML to merge with.")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging level.")
    args = parser.parse_args()
    logger.setLevel(args.log_level.upper())
    rasa_data_dict = convert_to_rasa_nlu_format(args.input_file)
    if rasa_data_dict:
        output_file_path = args.output_file if args.output_file else default_output_nlu_file
        final_rasa_data = rasa_data_dict
        if args.merge_with:
            logger.info(f"Attempting to merge with: {args.merge_with}")
            if os.path.exists(args.merge_with):
                try:
                    with open(args.merge_with, 'r', encoding='utf-8') as f: existing_nlu_data = yaml.safe_load(f)
                    if existing_nlu_data:
                        final_rasa_data = merge_nlu_data(existing_nlu_data, rasa_data_dict)
                        logger.info(f"Merged with {args.merge_with}")
                    else: logger.warning(f"Existing file {args.merge_with} empty/invalid. Using new data.")
                except Exception as e: logger.error(f"Error loading/merging {args.merge_with}: {e}. Using new data.")
            else: logger.warning(f"Merge file {args.merge_with} not found. Saving new data only.")
        try:
            output_dir = os.path.dirname(output_file_path)
            if output_dir: os.makedirs(output_dir, exist_ok=True)
            with open(output_file_path, 'w', encoding='utf-8') as f_out:
                yaml.dump(final_rasa_data, f_out, sort_keys=False, allow_unicode=True, width=1000)
            logger.info(f"Rasa NLU data saved to: {output_file_path}")
        except Exception as e: logger.exception(f"Error saving to {output_file_path}: {e}")
    else:
        logger.error("Conversion to Rasa NLU format failed."); sys.exit(1)
    logger.info("Annotation conversion process finished.")
