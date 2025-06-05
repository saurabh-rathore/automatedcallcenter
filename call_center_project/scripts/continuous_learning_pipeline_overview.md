# Continuous Learning Pipeline Overview

This document outlines the conceptual steps involved in the continuous learning pipeline for the automated call center bot. The goal is to iteratively improve the bot's NLU understanding and Knowledge Base based on real interactions, feedback, and new data.

## Data Sources for Learning

1.  **User Satisfaction Feedback:**
    *   Collected at the end of bot interactions (as implemented in `CallSession`).
    *   Stored in `feedback_log.txt` (or a database in production).
    *   Used to identify problematic conversations or areas where the bot is underperforming.

2.  **New Audio Recordings:**
    *   **Source:** Calls escalated to human agents, manually created recordings of new scenarios, etc.
    *   **Storage:** To be placed in `data/historical_recordings/` (or a designated cloud storage location).
    *   **Metadata:** Each recording should ideally be accompanied by metadata (date, source, reason for inclusion).

3.  **Bot Conversation Logs/Transcripts:**
    *   Detailed logs of bot-user interactions (including STT outputs, NLU interpretations, bot responses).
    *   (Future Enhancement) These would be stored systematically for review.

## Learning Workflow Steps

**Phase 1: Data Collection & Preparation**

1.  **Gather Data:** Consolidate new audio recordings and feedback logs.
2.  **Prioritize Review:** Use feedback scores (from `feedback_log.txt`) and bot failure metrics (e.g., high fallback rates, repeated NLU failures - requires more detailed logging) to prioritize conversations/recordings for review.
3.  **Transcription (for new audio):**
    *   Process new audio recordings through the Speech-to-Text (STT) engine (`GoogleCloudSTT` or chosen STT service).
    *   Store these transcriptions.

**Phase 2: Annotation & Knowledge Extraction (Human-in-the-Loop)**

*This phase typically requires a dedicated annotation interface or process, which is part of the Admin Portal's scope or a separate data annotation effort.*

1.  **Review Transcripts & Interactions:**
    *   Subject matter experts (SMEs) or data annotators review prioritized bot conversation transcripts and new recording transcripts.
2.  **STT Correction (if needed):** Correct any significant errors in STT output.
3.  **NLU Annotation/Correction:**
    *   Verify and correct intents and entities assigned by the NLU model (`RasaNLUParser`).
    *   Identify new intents or entities required for new scenarios.
    *   Add new example utterances for existing or new intents.
    *   Update `data/training_data/nlu/` files (e.g., `initial_training_data.yml`) with these changes.
4.  **Knowledge Base Update:**
    *   Identify gaps or inaccuracies in the current Knowledge Base (`data/knowledge_base/faqs.yml`, `data/knowledge_base/solutions.yml`).
    *   Extract new FAQs, solutions, or information from the reviewed recordings.
    *   Add or modify entries in the KB files.

**Phase 3: Model Retraining & KB Update**

1.  **NLU Model Retraining:**
    *   **Prerequisites:** Ensure Rasa (or chosen NLU tool) is installed.
    *   **Command (Example for Rasa):** `rasa train nlu --config <path_to_config.yml> --data data/training_data/nlu/ --out models/nlu/`
    *   This generates a new NLU model version in the `models/nlu/` directory.
2.  **Knowledge Base Update:** The KB files in `data/knowledge_base/` are already updated in Phase 2. Ensure they are saved and version-controlled.

**Phase 4: Evaluation & Deployment**

1.  **NLU Model Evaluation (Example for Rasa):**
    *   `rasa test nlu --nlu models/nlu/<new_model_name>.tar.gz --data data/training_data/nlu/`
    *   Review evaluation reports (e.g., intent accuracy, entity F1-score, confusion matrices).
    *   Decide if the new model is better than the current one.
2.  **End-to-End Testing:** Perform regression testing and test new scenarios with the updated NLU model and KB in a staging environment.
3.  **Deployment:**
    *   Replace the old NLU model file with the new, validated one.
    *   Ensure the bot application loads the updated KB files.
    *   This might involve restarting the bot application or having a mechanism to dynamically reload models/data.

**Phase 5: Monitoring & Iteration**

1.  **Monitor Performance:** Track bot performance metrics (call resolution rates, NLU confidence, fallback rates, user satisfaction) after deployment.
2.  **Iterate:** The pipeline is continuous. Repeat from Phase 1 as new data and feedback become available.

## Tools & Infrastructure (Conceptual)

*   **Audio Storage:** Cloud storage (GCS, S3).
*   **Annotation Tool:** (Admin Portal feature or third-party like Label Studio, Doccano, or Rasa X for NLU data).
*   **NLU Engine:** Rasa Open Source (or chosen platform).
*   **Version Control:** Git for training data, KB files, model configurations, and scripts.
*   **CI/CD Pipeline (Advanced):** For automating parts of the testing, training, and deployment process.
