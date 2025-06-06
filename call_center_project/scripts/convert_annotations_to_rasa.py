import json
import yaml
import os
import argparse
import logging
from collections import defaultdict
from datetime import datetime

# Setup logging
logger = logging.getLogger("AnnotationConverter")
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def convert_to_rasa_nlu_format(annotated_transcript_path):
    logger.info(f"Converting annotated transcript: {annotated_transcript_path}")
    try:
        with open(annotated_transcript_path, 'r', encoding='utf-8') as f:
            annotated_data = json.load(f)
            if not isinstance(annotated_data, list):
                logger.error("Annotated data is not a list of utterances as expected.")
                return None
    except FileNotFoundError:
        logger.error(f"File not found: {annotated_transcript_path}"); return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {annotated_transcript_path}: {e}"); return None
    except Exception as e:
        logger.exception(f"Unexpected error loading {annotated_transcript_path}: {e}"); return None

    intent_examples = defaultdict(list)
    processed_utterances = 0

    for utterance_data in annotated_data:
        original_text = utterance_data.get("text") # Use a distinct name for the original, immutable text
        intent = utterance_data.get("intent")
        entities = utterance_data.get("entities", [])

        if not original_text: # Check original_text
            logger.warning(f"Skipping utterance without 'text' field: {utterance_data}"); continue

        if intent:
            current_example_text = original_text # This is the text that will be built with markups

            if entities:
                entities.sort(key=lambda x: x.get("start_char", 0))

                parts = []
                current_pos_on_original_text = 0

                for entity in entities:
                    start = entity.get("start_char")
                    end = entity.get("end_char")
                    entity_type = entity.get("entity_type")

                    if None not in [start, end, entity_type]:
                        if start < current_pos_on_original_text or end > len(original_text) or start >= end:
                             logger.warning(f"Skipping invalid or overlapping entity in '{original_text}': {entity} (current_pos: {current_pos_on_original_text}, text_len: {len(original_text)})")
                             continue

                        # Append text segment from the original text
                        if start > current_pos_on_original_text:
                            parts.append(original_text[current_pos_on_original_text:start])

                        entity_value_from_original_text = original_text[start:end]
                        markup = f"[{entity_value_from_original_text}]({entity_type})"
                        parts.append(markup)

                        current_pos_on_original_text = end
                    else:
                        logger.warning(f"Skipping entity with missing fields in '{original_text}': {entity}")

                if current_pos_on_original_text < len(original_text):
                    parts.append(original_text[current_pos_on_original_text:])

                if parts: # Only join if entities were processed or text segments were added
                    current_example_text = "".join(parts)

            intent_examples[intent].append(f"- {current_example_text}")
            processed_utterances += 1
        else:
            logger.debug(f"Skipping utterance without 'intent' annotation: '{original_text[:50]}...'")

    if not intent_examples:
        logger.info("No utterances with intent annotations found."); return {"version": "3.1", "nlu": []}

    logger.debug("Intermediate intent_examples structure:")
    for intent_name_debug, examples_debug in intent_examples.items():
        logger.debug(f"  Intent: {intent_name_debug}")
        for ex_debug in examples_debug:
            logger.debug(f"    {ex_debug}")

    rasa_nlu_data = []
    for intent_name, examples_list in intent_examples.items():
        rasa_nlu_data.append({"intent": intent_name, "examples": "\n".join(examples_list)})

    logger.info(f"Successfully converted {processed_utterances} utterances."); return {"version": "3.1", "nlu": rasa_nlu_data}

def merge_nlu_data(existing_data, new_data):
    if not new_data or not new_data.get("nlu"): return existing_data
    if not existing_data or not existing_data.get("nlu"): return new_data
    existing_map = {item["intent"]: item for item in existing_data["nlu"]}
    for new_item in new_data["nlu"]:
        intent = new_item["intent"]; examples = new_item["examples"]
        if intent in existing_map:
            existing_map[intent]["examples"] = (existing_map[intent].get("examples","") + "\n" + examples).strip()
        else: existing_data["nlu"].append(new_item)
    return existing_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert annotated transcripts to Rasa NLU YAML.")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    parser.add_argument("--annotated-file", type=str, required=True, help="Path to annotated transcript JSON file.")
    default_out_name = f"converted_nlu_data_{datetime.now().strftime('%Y%m%d%H%M%S')}.yml"
    default_out_path = os.path.join(project_root, "data", "training_data", "nlu", default_out_name)
    parser.add_argument("--output-file", type=str, default=None, help=f"Path to save Rasa NLU YAML (default: {default_out_path}).")
    parser.add_argument("--merge-with", type=str, help="Optional: Path to existing Rasa NLU YAML to merge with.")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL"], help="Logging level.")
    args = parser.parse_args()

    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=args.log_level.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.setLevel(args.log_level.upper())

    rasa_data = convert_to_rasa_nlu_format(args.annotated_file)
    if rasa_data:
        out_path = args.output_file if args.output_file else default_out_path
        final_data = rasa_data
        if args.merge_with:
            logger.info(f"Attempting to merge with {args.merge_with}")
            if os.path.exists(args.merge_with):
                try:
                    with open(args.merge_with, 'r', encoding='utf-8') as f: existing = yaml.safe_load(f)
                    if existing: final_data = merge_nlu_data(existing, rasa_data); logger.info("Merge successful.")
                    else: logger.warning(f"Existing file {args.merge_with} empty/invalid. Using new data.")
                except Exception as e: logger.error(f"Error loading/merging {args.merge_with}: {e}. Using new data.")
            else: logger.warning(f"Merge file {args.merge_with} not found. Saving new data.")
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, 'w', encoding='utf-8') as f: yaml.dump(final_data, f, sort_keys=False, allow_unicode=True, width=1000)
            logger.info(f"Rasa NLU data saved to: {out_path}")
        except Exception as e: logger.exception(f"Error saving to {out_path}: {e}")
    else:
        logger.error("Conversion failed."); sys.exit(1)
    logger.info("Conversion process finished.")
