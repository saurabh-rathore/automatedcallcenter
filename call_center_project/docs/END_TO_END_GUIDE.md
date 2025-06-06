# Your Guide to the Automated Call Center Bot

Welcome! This guide is designed to help you understand how our Automated Call Center Bot works, from initial setup to everyday use and improvement. It's for anyone who will be using or overseeing the bot, especially those who might not have a deep technical background.

**Our Goal:** To provide a helpful, automated assistant that can answer common customer questions and resolve issues, making your call center more efficient.

---

## Phase 0: Getting Started & What You'll Need

Setting up and launching the call center bot involves some technical steps. **You'll need a technical team or a dedicated technical person to handle the initial setup and ongoing maintenance.** Here’s a quick overview of what they'll need:

*   **Access to Project Code:** The technical team will need access to the bot's software, which is stored in a code repository (like Git).
*   **Cloud Service Accounts:** To make the bot smart (like understanding speech and talking back), it uses cloud services (e.g., from Google Cloud or Amazon Web Services). Your technical team will manage these accounts and any associated costs.
*   **Telephony Provider Account:** To connect the bot to your phone lines, an account with a telephony provider (like Twilio or a similar service) is needed. Your technical team will set this up.

---

## Phase 1: Preparing Your Initial Data

The bot learns from data. The more relevant data you provide, the smarter it becomes!

### 1. Call Recordings: The Bot's Learning Material

*   **Why they're important:** Past call recordings help us understand how your customers talk, what questions they ask, and the common issues they face. This is key for training the bot.
*   **How to prepare them:**
    *   **Quality is key:** Clear audio recordings work best.
    *   **Common formats:** Standard audio files like WAV or MP3 are preferred.
    *   **Where to put them (initially):** Your technical team might ask you to place an initial batch of recordings in a specific folder (e.g., `data/raw_transcripts/` in the project). Later, you'll be able to upload new recordings directly through the Admin Portal.
*   **What happens next?** These audio files will be converted into text (a process called "transcription") so the bot can understand the conversations.

### 2. Knowledge Base (KB) Content: The Bot's Brain

*   **What it is:** The Knowledge Base is like the bot's reference manual. It contains:
    *   **FAQs (Frequently Asked Questions):** Common questions and their answers.
    *   **Solutions:** Step-by-step guides to resolve common problems.
*   **Where it lives:** This information is stored in simple text files (e.g., `data/knowledge_base/faqs.yml` and `data/knowledge_base/solutions.yml`).
*   **How to edit (simplified):** Your technical team can help you update these files, or if you're comfortable with simple text editing, you might be able to make small changes. The format is called YAML, which is human-readable.

    **Example of a simple FAQ in `faqs.yml`:**
    ```yaml
    faqs:
      - id: faq_opening_hours # A unique name for this FAQ
        intent: get_opening_hours # What the user is trying to find out
        question_variants: # Different ways users might ask
          - "What are your opening hours?"
          - "When are you open?"
        answer: "We are open Monday to Friday, 9 AM to 5 PM."
        tags: ["hours", "support_times"]
    ```
    **Focus on:**
    *   `question_variants`: Add as many different ways a user might ask the same question.
    *   `answer`: Provide a clear, concise answer.

    **Example of a simple Solution in `solutions.yml`:**
    ```yaml
    solutions:
      - id: sol_reset_password # Unique name
        problem_description: "User forgot password and needs to reset it"
        steps:
          - text: "I can help you with that. First, please go to our website's login page."
          - text: "Click on the 'Forgot Password?' link."
          - text: "Follow the instructions sent to your email to create a new password."
    ```
    **Focus on:**
    *   `problem_description`: A clear summary of the issue.
    *   `steps`: The `text` under each step provides the instructions the bot will give.

    Your technical team will ensure this data is correctly formatted and loaded into the system.

---

## Phase 2: How the Bot Learns (Initial Training - Simplified)

Once your data is ready, it's used to "train" the bot.

1.  **Transcription (Speech-to-Text, STT):**
    *   Your call recordings (audio) are converted into written text using an STT service.
    *   This service requires an "API Key" (like a special password for computer programs to talk to each other). Your technical team will configure this.

2.  **Understanding User Language (NLU Training):**
    *   **What it is:** NLU (Natural Language Understanding) is how the bot figures out what a user is trying to do (their "intent") and picks out important pieces of information ("entities," like dates, names, or product types) from their messages.
    *   **Annotation:** To train the NLU, someone (often a specialist, or using special software tools that might be part of the Admin Portal in the future) reviews the transcribed user messages. They label these messages with the correct intents and highlight the entities. This is called "annotation."
    *   **Training the Model:** The annotated text is then fed into a training process (our project uses scripts like `parse_transcriptions.py`, `convert_annotations_to_rasa.py`, and `train_nlu.py`). This process creates an NLU model – a special file that the bot uses to understand new user messages.
    *   **Who does this?** Your technical team will typically run these training processes. Later, some of these functions might be available to trigger through the Admin Portal.

---

## Phase 3: Setting Up API Keys (A Note for Awareness)

*   As mentioned, services like Speech-to-Text (STT) and Text-to-Speech (TTS, for the bot to talk back) need API Keys.
*   **Important:** These keys are like passwords for these services and are very sensitive. **Your technical team will securely configure these keys on the server where the bot runs.** You will not need to handle these keys directly in configuration files for a live system. The Admin Portal might have a placeholder for an API key for STT uploads for development/testing with the placeholder STT service, but this is different from the main production keys.

---

## Phase 4: Getting the Bot Online (Deployment - High Level)

"Deployment" is the process of taking the bot software and making it live so it can handle calls.

*   **Servers:** The bot software needs to run on a computer (a "server"), which could be in the cloud or one of your company's servers.
*   **Packaging:** Your technical team will use files like the `Dockerfile` (a list of instructions for packaging the bot) and the `docs/deployment_overview.md` (a more technical guide for them) to prepare the bot for deployment.
*   **Telephony Connection:** The technical team will also configure your telephony provider (e.g., Twilio) to connect your business phone number(s) to the running bot application. When a customer calls, the call will be routed to the bot.

---

## Phase 5: Using Your Deployed Call Center Bot & Admin Portal

Once the bot is live, you'll interact with it primarily through the **Admin Portal**. Your technical team will provide you with a web address (URL) to access it.

1.  **Logging In:**
    *   You'll need a username and password (provided by your technical team) to log in. Our current system has a placeholder login (e.g., `admin` / `password123`).

2.  **Dashboard:**
    *   This is the main overview page. You'll see key metrics like:
        *   **Total Calls Today:** How many calls the bot system handled.
        *   **Calls Handled by Bot:** How many calls were resolved by the bot without needing a human.
        *   **Calls Escalated to Human:** How many calls were transferred to a human agent.
        *   **Average Satisfaction:** A score based on customer feedback (e.g., from a "Were you satisfied?" question at the end of calls). This helps you see how happy customers are with the bot.
        *   **Fallback Rate:** Percentage of times the bot couldn't understand the user and had to give a generic response (like "I'm sorry, I don't understand").
        *   **Common Intents:** What users are most frequently asking about.

3.  **Managing Recordings & Transcripts (via "Manage Transcribed Recordings" page):**
    *   **Uploading New Audio:** You can upload new call recordings (e.g., if a human agent handled a call that you think the bot could learn from). The bot will use its STT service to convert this audio to text.
    *   **Viewing List:** See a list of audio files that have been uploaded for STT.
    *   **Status:** Check if a transcript is available for each audio file.
    *   **Viewing Transcripts:** Click on a transcript file to read the text version of the call.

4.  **NLU Model Management (via "NLU Model Management" page):**
    *   **Retraining:** There's a button here to "Retrain NLU Model." Clicking this tells the system to use the latest NLU training data (from annotated transcripts) and Knowledge Base content to update and improve the bot's understanding. This process runs in the background.
    *   **Status:** You can see a summary of the latest retraining process (e.g., if it was successful, when it ran, etc.).

5.  **Knowledge Base Management (Conceptual - via "KB Management" page):**
    *   **Viewing:** This page will show you the current FAQs and Solutions loaded into the bot's Knowledge Base.
    *   **Editing/Adding (Future):** In a fully implemented system, this section would allow you to directly edit, add, or delete FAQs and Solutions through the Admin Portal interface, making it easier to keep the bot's knowledge up-to-date without directly editing YAML files.

---

## Phase 6: Keeping the Bot Improving (Continuous Learning)

The bot isn't a "set it and forget it" system. It learns and improves over time!

*   **Upload New Recordings:** Regularly upload new call recordings, especially for:
    *   Calls that were escalated to human agents (these show where the bot struggled).
    *   New types of customer queries or new product information.
*   **Retrain the NLU Model:** After new data has been transcribed and "annotated" (intents/entities labeled by your team or specialists), use the "Retrain NLU Model" button in the Admin Portal. This makes the bot smarter.
*   **Feedback Log (`feedback_log.txt`):** The system keeps a log of user satisfaction feedback. Reviewing this (currently a text file, but could be part of the Admin Portal later) helps identify calls or topics where users weren't satisfied, pointing to areas for improvement in NLU or KB content.
*   **Review and Update KB:** Regularly check if the FAQs and Solutions in your Knowledge Base are still accurate and complete. Update them as needed (conceptually through the Admin Portal in the future, or by editing the YAML files with technical help).

---

## Glossary (Simple Definitions)

*   **Admin Portal:** A web interface for you to manage and monitor the call center bot.
*   **Annotation:** The process of labeling text (like call transcripts) with intents and entities to teach the NLU model.
*   **API Key:** Like a password that computer programs use to access a service (e.g., STT or TTS services).
*   **Deployment:** The process of making the bot software live and operational on a server.
*   **Intent:** What the user is trying to achieve (e.g., `get_opening_hours`, `report_issue`).
*   **Entity:** A key piece of information in a user's message (e.g., a date, a location, a product name).
*   **Knowledge Base (KB):** The bot's "brain" or reference manual, containing FAQs and Solutions.
*   **NLU (Natural Language Understanding):** How the bot understands the meaning behind human language.
*   **Server:** A powerful computer that runs the bot software and makes it accessible.
*   **STT (Speech-to-Text):** Converts spoken audio into written text.
*   **TTS (Text-to-Speech):** Converts written text into spoken audio (how the bot talks).
*   **YAML:** A human-readable text format used for configuration files and the Knowledge Base.

---

**Disclaimer:** This guide simplifies many of the technical details involved in setting up, deploying, and maintaining the automated call center bot. A skilled technical team is essential for these aspects, especially for ensuring the system is secure, scalable, and reliable. Always work closely with your technical team for any setup, configuration changes, or troubleshooting.
