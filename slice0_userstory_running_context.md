1. Product Summary
ResKiosk is an offline-first, local-network kiosk system for disaster shelters, evacuation centers, and similar humanitarian response settings. It combines an Android kiosk app, a local hub/backend, and an admin console so people in a shelter can ask questions by voice or text and receive answers without depending on public internet access. The system is built around locally hosted retrieval, translation, and response formatting, with emergency alert handling and shelter information management included in the same product.

It is primarily for shelter residents who need fast access to operational information, and for shelter staff who need to manage that information, monitor emergencies, and oversee kiosks on site. It operates in constrained environments where connectivity may be unreliable, staffing may be stretched, and information must still be delivered consistently across multiple languages and devices.

2. Product Purpose
The purpose of ResKiosk is to provide reliable, multilingual, offline-capable access to shelter information through a kiosk experience, while giving operators local tools to manage knowledge, shelter configuration, kiosk connectivity, and emergency workflows.

3. Primary Users
3.1 Shelter Residents / Displaced Individuals
People inside a shelter or evacuation site who need information about food, registration, medical help, sleeping areas, transportation, announcements, safety, and other available services.

3.2 Shelter Staff / Operators
Staff or responders who maintain the knowledge base, update shelter configuration, review logs, track frequently asked questions, manage emergencies, and monitor kiosk connectivity.

3.3 Technical Operators
Team members responsible for hub setup, local deployment, kiosk connection, model availability, and optional LoRa relay or inter-hub messaging setup.

4. Problem Statement
In disaster and evacuation settings, people need timely, clear information, but staff may be overwhelmed, language differences may slow communication, and internet connectivity may be unavailable or unstable. ResKiosk addresses this by providing a local, offline-first kiosk and hub system that can answer common shelter questions, support multilingual interaction, and escalate emergencies through a structured workflow.

5. Current Product Scope
ResKiosk currently consists of three core components:

5.1 Hub + Console
A local Python/FastAPI hub with a React admin console. This component handles query processing, semantic retrieval, translation, response formatting, knowledge base operations, shelter configuration, emergency lifecycle management, kiosk registration, query logging, FAQ tracking, and optional LoRa-related messaging and monitoring.

5.2 Kiosk Android App
An Android tablet application built in Kotlin/Jetpack Compose. It provides the user-facing kiosk experience, including voice input, typed input, offline/local speech handling, multilingual UI flows, answer playback, emergency detection, SOS triggering, session handling, and feedback capture.

5.3 ResKiosk RELAY / LoRa Messaging Layer
An optional relay and hub-messaging layer integrated into the hub and console. It supports LoRa-based message transport, monitoring, connection management, acknowledgments, and optional AES-256-GCM encryption for constrained communication environments.

6. Current Core Capabilities
6.1 Voice and Text Question Intake
Users can interact with the kiosk by speaking or by typing, depending on the current kiosk mode.

6.2 Local Query Processing and Semantic Retrieval
The hub receives kiosk queries, normalizes them, classifies intent, performs semantic search against the local knowledge base, and returns the best available answer or a clarification/fallback response.

6.3 Multilingual Support
The system supports multilingual interaction across the kiosk and hub workflow, including translation of incoming queries and outgoing answers.

6.4 Spoken Response Delivery
The kiosk can present answers visually and play them back as spoken responses.

6.5 Emergency Detection and Response Management
The kiosk can detect emergency phrases or accept manual SOS activation, send alerts to the hub, and reflect emergency status changes as staff acknowledge, respond to, resolve, or dismiss alerts in the console.

6.6 Shelter Information and Knowledge Management
Operators can manage shelter configuration and knowledge base content through the admin console, including freshness enforcement for shelter sections and KB-backed answer management.

6.7 Kiosk, Network, and Messaging Operations
Operators can view hub connection info, register and name kiosks, monitor connected devices, and use hub-to-hub or relay-oriented messaging tools where LoRa hardware is available.

6.8 Logging, FAQ Tracking, and Feedback Capture
The system records query logs, tracks frequently asked questions, and stores kiosk thumbs-up/thumbs-down feedback for later retrieval-bias updates.

7. Current High-Level Workflow
A user starts a kiosk session and asks a question by voice or text.

The kiosk captures the input, applies local speech/text cleanup, and sends the query to the hub over the local network.

The hub translates the query to English when needed and runs normalization, intent classification, and semantic retrieval against the local knowledge base.

If a strong result is found, the hub formats the answer; if not, it may return a clarification or fallback response.

The hub translates the final answer back to the user’s language when needed and returns it to the kiosk.

The kiosk displays the response and plays spoken output.

If the interaction contains emergency intent, the kiosk can trigger an emergency alert that staff then manage through the hub and console workflow.

8. Current Technical Boundaries
ResKiosk is designed as an offline-first system; cloud integration is currently disabled in the current codebase.

The kiosk does not operate as a fully standalone answer engine; it depends on communicating with the local hub for retrieval and answer generation.

The hub and admin console are built with Python, FastAPI, SQLite, React, and Vite.

The kiosk is built as an Android app using Kotlin and Jetpack Compose.

Local AI/model components include embedding-based retrieval, local translation, local/offline speech tooling, and local LLM-based formatting/rewriting.

The system is intended to run over local LAN, with optional LoRa-based messaging/relay support for constrained environments.

LoRa capabilities depend on attached hardware and local serial/Bluetooth connectivity.

9. Current Non-Scope / Not Yet Defined
This document describes the current-state product reflected by the codebase. It does not define:

future roadmap items that are not currently implemented

cloud-first or internet-dependent operating modes

commercialization, organizational rollout, or procurement strategy

cross-organization deployment policy or governance model

guarantees that every documented feature is production-hardened across all environments and languages

10. Open Questions / Validation Items
Which current features are production-ready versus still prototype-level?

How complete and field-tested is the LoRa/RELAY workflow with actual hardware?

Which supported languages are fully validated end to end across STT, translation, UI, and TTS?

How consistently are kiosk setup, model download, and asset provisioning handled across devices?

How often is RLHF-style feedback bias rebuilding actually run in practice?

Which console pages are considered operationally complete for live deployments?

For every important action or decision, you MUST first review `slicex_goalx_context.md` and use it as your source of truth.
For every action you take, you MUST update `slicex_goalx_context.md` with relevant context, including:
- Subtasks (based on the main user story)
- Decisions made and why
- What you are currently doing
- What has been completed
- What is still remaining
Once the user story is fully delivered, you MUST add a **Story Implementation Summary** describing what was done and the final outcome.

EXPLICITLY STOP development once user story is delivered fully. DO NOT go out of user story scope