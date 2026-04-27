# ResKiosk Voice Pipeline: STT to TTS (including RLHF & Feedback)

**Note:** Cloud integration is currently disabled. This document reflects the offline-first local pipeline only.

This document provides a comprehensive, step-by-step breakdown of the ResKiosk voice pipeline. It covers everything from the moment the user speaks to the voice output they hear, detailing language-specific differences, backend retrieval, the rewrite/format steps, and the reinforcement learning from human feedback (RLHF) loop.

---

## 1. Voice Capture & Speech-to-Text (STT)

### 1.1 Audio Recording
When the user taps to speak on the Kiosk (Android application):
1. `AudioRecorder` starts picking up audio. Memory buffers accumulate 16kHz audio samples.
2. Noise suppression algorithms are dynamically enabled **only for English (`en`) and Japanese (`ja`)**.
3. For Spanish (`es`), German (`de`), and French (`fr`), the raw mic data bypasses noise suppression because the underlying STT engine for these languages performs better on raw audio.

### 1.2 STT Decoding Strategies (Streaming vs. Batch)
The system pipes the audio chunks to the `SherpaSttEngine`. There are two distinct language handling paths:
- **Streaming Languages (`en`, `ja`)**: These use Sherpa-ONNX Zipformer models. They continuously decode audio, streaming a real-time transcript to the UI as the user speaks.
- **Batch Languages (`es`, `de`, `fr`)**: These use localized Whisper models. Whisper processes audio in chunks and only returns a final transcript at the end. To compensate for the lack of real-time text, the Kiosk UI displays a temporary "Listening..." placeholder.

### 1.3 Post-Processing & Punctuation
Once STT finishes transcribing:
1. **Correction**: The raw string is run through `SttPostProcessor` to fix domain-specific hallucinations and misrecognized shelter terms.
2. **Punctuation**: The `OfflinePunctuation` ONNX model injects formatting (periods, question marks, commas). This step is skipped for Batch (Whisper) languages, as Whisper inherently predicts proper punctuation natively.
3. **Emergency Check**: `EmergencyDetector` analyzes the transcript for crisis keywords (e.g., "Help", "SOS"). If an emergency is detected, it overrides the standard pipeline.
4. **Intonation Analysis**: `analyzeIntonation` examines the raw audio, punctuation signals, and lexical patterns to compute an `intonation_confidence` and flag whether the user asked a "question" or made a "statement".

## 2. Inbound Hub Processing & Translation

The Kiosk issues a `POST /query` payload to the Hub module containing:
- The finalized English and Original transcripts.
- The `query_type` and `intonation_confidence`.
- The native UI `language`.
- Any historical `session_id` or excluded results.

### 2.1 Inbound Translation
If the user's native language is not English, the system activates the local Facebook **NLLB-200-distilled-600M** model (`translator.py`). It translates the inbound request directly into English to standardize querying against the Knowledge Base (KB).

## 3. Query Retrieval & Filtering (Semantic Search)

The Hub's `search.retrieve` module takes the normalized English query through a multi-tiered evaluation:

### 3.1 Direct Config & Inventory Checks
- The system checks if the text matches any Hardcoded Shelter Configurations.
- `inventory_module` performs regex-based checks to instantly answer questions about current stock (e.g., food, blankets) without semantic processing.

### 3.2 Intent Classification
The string passes through an intent classifier.
- **Bypass**: Simple intents like "greeting", "goodbye", or "small_talk" bypass the main vector database entirely, returning safe canned English replies instantly.
- **Enrichment**: Core intents (e.g., "food", "medical") structurally append rich keyword expansions to the search string (e.g. appending "eat meals cafeteria breakfast..." to a "food" query) to dramatically improve vector hits.

### 3.3 Vector Search (Sentence Transformers)
- The enriched query string is embedded into a dense vector (using `sentence-transformers/all-MiniLM-L6-v2`).
- Cosine similarity scores (`raw_cosine`) are computed against the pre-loaded dictionary of available Knowledge Base `KBArticle` vectors.

### 3.4 Feedback Dislike Filtering
- The Kiosk may supply `exclude_source_ids` (from a previous disliked interaction). The Hub explicitly removes these `source_id` vectors from the `top_k` results so the exact same article isn't served twice.

### 3.5 Reinforcement Learning from Human Feedback (RLHF)
If `RESKIOSK_RLHF_ENABLED` is true:
- The backend applies a positive or negative bias offset to the raw cosine scores using a configurable parameter `RLHF_ALPHA` (default 0.10).
- The equation transforms the score: `score = max(0.0, min(1.0, raw_cosine + (RLHF_ALPHA * historical_bias)))`.
- This calculation rearranges the top answers based on the community's past collective likes and dislikes for those articles.

### 3.6 Evaluation Thresholds
The system selects the top-scoring article (`top_k[0]`) and routes it based on confidence ranges:
- **`DIRECT_MATCH`** (Score $\ge$ 0.60): A definitive answer was found.
- **`NEEDS_CLARIFICATION`** (0.40 $\le$ Score < 0.60): Ambiguous. The Hub returns localized category suggestions to ask the user to specify their concern.
- **`NO_MATCH`** (Score < 0.40): The search failed to find relevant data.

## 4. LLM Query Rewrite (Fallback)

If a query hit `NO_MATCH` or `NEEDS_CLARIFICATION`:
- If the original STT output looks messy (noisy transcripts with word-counts between 4 and 30 characters and unclear intent), the Hub dynamically boots **Ollama (`llama3.2:3b`)**.
- The LLM's only job in this step is to scrub/rewrite the noisy speech-to-text string into a single clear, sanitized sentence constraint.
- The pipeline executes Step 3 entirely again using this rewritten query to see if it uncovers a `DIRECT_MATCH`.

## 5. LLM Response Formatting

For successful `DIRECT_MATCH` retrievals tied to a structured KB Article:
- The system hands the exact backend JSON article contents to the local Ollama LLM (`formatter.py`).
- Grounded strictly in the `SYSTEM_PROMPT` rules, the model synthesizes the dense database entry into 2-4 conversational, simple English sentences suitable for a stressed evacuee. Short conversational history (if any) is injected for context.

## 6. Outbound Hub Processing (Translation)

- The final answer text (from formatting, fallback, intent bypass, or rewriting) is formulated in English.
- If the originating user's Kiosk `language` is not English, the system passes the text back through the **NLLB-200** model to translate the response *back* to the native language.
- The entire transaction, latency, top scores, and RLHF values are recorded to the SQLite log database (`schema.QueryLog`). 
- The formatted response is transmitted down to the Kiosk.

## 7. Outbound Kiosk Delivery (TTS)

- The Kiosk receives the response and renders it into a visual `ChatMessage` bubble.
- **Text-to-Speech**: The text string is handed to the `SherpaTtsEngine` loaded with the proper acoustic language model, and it vocalizes the response audibly across the shelter kiosk hardware.

---

## 8. The Feedback Loop Flow (Likes & Dislikes)

When the response bubble drops on screen, the Kiosk exposes a generic interactive widget:

### 8.1 Firing a Like (+1)
- User hits thumbs-up. The Kiosk asynchronously fires a `POST /feedback` command back to the Hub with `label = 1` tying it to the article's `source_id`.
- Over time, the Hub's RLHF calculator accumulates this positive offset, making this KB Article rank higher in the Cosine calculations for future evacuees asking similar variants.

### 8.2 Firing a Dislike (-1) & Retry Pathway
A dislike triggers a robust self-correction pipeline:
1. **Network Logging**: UI asynchronously fires a `POST /feedback` containing the `label = -1` payload back to the Hub to decrement rank offset.
2. **State Manipulation**: On the Kiosk, the UI registers that a specific `source_id` failed. It pushes that `source_id` into a running local slice of `exclude_source_ids`.
3. **Silent Retrying**: The Kiosk immediately triggers a fresh `POST /query` search natively. 
   - It submits the **exact** original English query text from the STT memory block.
   - It attaches the newly updated array of `exclude_source_ids`.
   - The UI blocks with a "Retrieving a new response..." temporary dialog.
4. **Hub Redirection**: As outlined in Step 3.4, the Hub strips the exact article out of the Vector pipeline completely. It computes the new best hit logically beneath it and executes the rewrite/format steps as necessary.
5. **Final Delivery**: The new, alternative response is translated and spoken out loud, essentially resolving the friction of a bad answer by retrieving the next valid option.

--- 

## 9. Core Technologies & Models Summary

To execute this entire offline pipeline, the architecture leverages the following specialized models and technologies:

**Kiosk (Frontend)**
- **Platform:** Android (Kotlin)
- **Voice Engine:** `Sherpa-ONNX` (Offline STT and TTS engines)
- **STT Streaming Models:** Zipformer architectures (for `en`, `ja`)
- **STT Batch Models:** Whisper ONNX derivations (for `es`, `de`, `fr`)
- **Punctuation Model:** `OfflinePunctuation` ONNX model
- **TTS Models:** VITS-based acoustic language models (via Sherpa)

**Hub (Backend)**
- **Platform:** Python / FastAPI
- **Database:** SQLite (via SQLAlchemy) for `KBArticle`, `StructuredConfig`, and `QueryLog` storage.
- **Translation:** `facebook/nllb-200-distilled-600M` (via HuggingFace)
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (Cosine similarity computed directly via `numpy`)
- **LLM Engine:** Local `Ollama` running the `llama3.2:3b` model.

*End of Pipeline Overview.*

---

 
