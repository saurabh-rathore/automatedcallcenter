# Deployment Overview for Call Center Bot

This document provides a high-level overview of considerations and a conceptual plan for deploying the automated call center bot application to a production or staging environment.

## 1. Target Environment

*   **Cloud Platform:** Considerations include AWS, Google Cloud Platform (GCP), or Azure. The choice depends on existing infrastructure, preferred services, and cost.
*   **Compute Options:**
    *   **Kubernetes (EKS, GKE, AKS):** Offers scalability, resilience, and declarative configuration. Suitable for microservices architecture (e.g., separate services for bot logic, NLU, admin portal).
    *   **Virtual Machines (EC2, Compute Engine, Azure VMs):** Simpler to start with for monolithic deployments or smaller setups. Requires manual scaling and management.
    *   **Serverless Functions (AWS Lambda, Google Cloud Functions, Azure Functions):** Potentially for parts of the system like webhook handlers or asynchronous tasks, but the main call session logic might be too long-running or stateful for simple serverless functions.
    *   **Managed Application Platforms (Elastic Beanstalk, App Engine, Azure App Service):** Abstract away some infrastructure management.

## 2. Telephony Integration

*   **Providers:** Integration with a telephony provider is crucial (e.g., Twilio, Vonage/Nexmo, SignalWire, or existing enterprise SIP infrastructure).
*   **Mechanism:**
    *   **Webhooks:** Most cloud telephony providers use webhooks to send events (incoming call, DTMF tones, speech streams) to the bot application. The bot application needs a public-facing API endpoint.
    *   **SIP (Session Initiation Protocol):** For direct integration with SIP trunks. This might involve using libraries like `PJSIP` or dedicated media gateways.
*   **Real-time Audio Streaming:** The bot needs to receive real-time audio streams from the telephony provider for STT and send audio streams back for TTS. Protocols like RTP or WebSockets (via media gateways) are common.

## 3. AI Services Integration

*   **Speech-to-Text (STT) & Text-to-Speech (TTS):**
    *   Use chosen cloud provider services (e.g., Google Cloud STT/TTS, AWS Transcribe/Polly).
    *   Requires API keys/SDKs and proper authentication (e.g., service accounts, IAM roles).
    *   Ensure network connectivity from the bot application to these services.
*   **Natural Language Understanding (NLU):**
    *   **Self-hosted (e.g., Rasa):** If using Rasa NLU, the trained model (`models/nlu/`) needs to be deployed. This could be:
        *   Embedded within the main bot application container (simpler for small scale).
        *   As a separate microservice (recommended for scalability and independent updates). This service would expose an HTTP API for parsing text.
    *   **Cloud-based NLU (e.g., Dialogflow, Lex):** Requires API keys/SDKs.

## 4. Knowledge Base (KB)

*   **Production Storage:**
    *   **YAML/JSON files (as currently):** Suitable for smaller KBs that don't change extremely frequently. Requires redeployment or a reload mechanism for updates.
    *   **Database (NoSQL or SQL):** Recommended for larger, more dynamic KBs. Allows updates via the Admin Portal without redeploying the bot application. Options: PostgreSQL, MySQL, MongoDB, Firestore, DynamoDB.
    *   **Vector Database:** For semantic search capabilities within the KB.
*   **Access:** The `KnowledgeBaseService` would need to be adapted to read from the chosen production storage.

## 5. Admin Portal Deployment

*   **Separate Web Application:** The Admin Portal (e.g., Flask app in `src/admin_portal/`) should typically be deployed as a separate web application (different container/service).
*   **Authentication & Authorization:** Secure access for administrators.
*   **Database Backend:** Would need its own database to store admin users, configurations, and potentially to manage/view NLU training data, KB content, and feedback logs if not stored elsewhere.

## 6. Data Storage (Persistent)

*   **Feedback Logs (`feedback_log.txt`):** In production, write to a structured logging system (e.g., ELK stack, Splunk, CloudWatch Logs, Google Cloud Logging) or a database.
*   **Conversation Transcripts/Logs:** Store detailed interaction logs for analysis, debugging, and continuous learning. A database or dedicated log management system is essential.
*   **Audio Recordings (`data/historical_recordings/`):** Use cloud object storage (AWS S3, Google Cloud Storage, Azure Blob Storage) for scalability and durability. The Admin Portal's upload feature should target this storage.

## 7. Configuration Management

*   **Environment Variables:** For non-sensitive configuration.
*   **Secrets Management:** Use tools like HashiCorp Vault, AWS Secrets Manager, Google Secret Manager, or Kubernetes Secrets for API keys, database credentials, etc. Avoid hardcoding secrets.

## 8. Scalability & Reliability

*   **Horizontal Scaling:** Design components (bot application, NLU service, admin portal) to be stateless where possible to allow running multiple instances behind a load balancer.
*   **Resilience:** Implement health checks, automated restarts, and potentially failover mechanisms.
*   **Database Scalability:** Choose a database solution that can scale and ensure proper indexing and query optimization.

## 9. Monitoring & Logging

*   **Application Performance Monitoring (APM):** Tools like Prometheus, Grafana, Datadog, Dynatrace.
*   **Centralized Logging:** ELK Stack, Splunk, cloud provider logging services.
*   **Bot-specific Metrics:** Track NLU confidence, fallback rates, intent distribution, call duration, user satisfaction.

## 10. CI/CD (Continuous Integration/Continuous Deployment)

*   **Version Control:** Git (already in use conceptually).
*   **Automated Pipeline:**
    *   Linting and static analysis.
    *   Automated unit, integration, and E2E tests.
    *   Automated NLU model training and evaluation (as outlined in `continuous_learning_pipeline_overview.md`).
    *   Building Docker images.
    *   Pushing images to a container registry (Docker Hub, ECR, GCR, ACR).
    *   Automated deployment to staging and production environments.
    *   Tools: Jenkins, GitLab CI, GitHub Actions, CircleCI.

## Conceptual Phased Deployment Plan

1.  **Phase 1: Infrastructure & Core Services Setup**
    *   Set up cloud environment (VPC, Kubernetes cluster or VMs).
    *   Provision databases and object storage.
    *   Set up secrets management.
    *   Configure STT, TTS AI services with API keys.

2.  **Phase 2: NLU Service & Initial Model Deployment**
    *   Deploy the chosen NLU engine (e.g., Rasa server) with an initial trained model.
    *   Test NLU service API.

3.  **Phase 3: Bot Application Deployment**
    *   Containerize the core bot application (Python logic, `CallHandler`, `CallSession`, services).
    *   Configure it to connect to the deployed NLU service and AI services (STT, TTS).
    *   Deploy to the chosen compute environment.
    *   Implement basic API endpoints for telephony webhooks.

4.  **Phase 4: Telephony Integration**
    *   Configure telephony provider to point to the bot application's webhook API.
    *   Test basic call setup, audio streaming (STT/TTS), and teardown.

5.  **Phase 5: Knowledge Base & Admin Portal**
    *   Migrate KB to production storage (if not file-based).
    *   Deploy the Admin Portal application.
    *   Ensure Admin Portal can interact with required data stores (e.g., for recordings, feedback).

6.  **Phase 6: Testing & Refinement**
    *   Conduct thorough E2E testing, including different call flows and edge cases.
    *   User Acceptance Testing (UAT).
    *   Performance and load testing.

7.  **Phase 7: Go-Live & Monitoring**
    *   Deploy to production.
    *   Implement comprehensive monitoring and logging.
    *   Initiate the continuous learning pipeline.

This overview serves as a starting point. Each area requires detailed planning and design based on specific project requirements and chosen technologies.
