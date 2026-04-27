# Intent and Classification Engine (ResKiosk Hub)

This document describes how the Hub classifies user queries into intents, how it uses those intents to enrich retrieval, and where thresholds and configuration live.

## Overview

The Hub uses a **prototype-based intent classifier** built on the same **MiniLM sentence embedder** used for semantic search. Intent classification is used to:

- Enrich queries with intent-specific keywords before semantic search.
- Gate clarification prompts.
- Short-circuit small-talk and simple conversational intents without hitting the KB.

Intent classification happens inside `hub/retrieval/search.py` during `retrieve()` and is initialized at startup in `hub/main.py`.


## Key Files

- `hub/retrieval/intent.py`: prototype-based classifier (intent labels + prototype phrases).
- `hub/retrieval/search.py`: retrieval pipeline + intent-based enrichment + clarification gating.
- `hub/retrieval/normalizer.py`: normalization that runs before intent and embedding.
- `hub/main.py`: initializes embedder + intent classifier at startup.


## Pipeline (Simplified)

1. **Normalize query** (language-aware) via `normalize_query()`.
2. **Inventory check** (special-case shortcut for supplies).
3. **Intent classification** using prototype embeddings.
4. **Short-circuit for small-talk / identity / goodbye** intents if high confidence.
5. **Enrich query** with intent keywords (if confident; can use top-2 intents).
6. **Embed + search** across KB embeddings.
7. **Clarification gating** (if intent is unclear + low score).
8. **Compound follow-up** (single primary answer + optional secondary follow-up prompt).


## Intent Classifier

**File:** `hub/retrieval/intent.py`

- Uses **prototype phrases** per intent.
- Computes **centroids** for each intent by embedding all prototypes and averaging.
- Classifies by **cosine similarity** between query embedding and intent centroids.
- Returns:
  - `(intent, score)` if score >= `UNCLEAR_THRESHOLD`
  - `("unclear", score)` if below threshold

### Top-2 Classification (Dual Enrichment + Compound Detection)

The classifier also supports a **top-2** variant used by retrieval:

- `classify_top2()` returns `(best_intent, best_score, second_intent, second_score)`.
- Compound mode is enabled when:
  - `best_score >= RESKIOSK_COMPOUND_INTENT_MIN`
  - `second_score >= RESKIOSK_COMPOUND_INTENT_MIN`
  - `abs(best_score - second_score) <= RESKIOSK_COMPOUND_GAP_MAX`
- If compound mode is active, the system applies safety-first arbitration:
  - `safety/emergency > medical > children/special_needs > other service intents`
- The winner becomes `primary_intent`; the other becomes `secondary_intent`.

### Intent Labels

```
greeting
identity
capability
small_talk
food
medical
registration
sleeping
transportation
safety
facilities
lost_person
pets
donations
hours
location
general_info
goodbye
inventory
mental_health
legal_docs
financial_aid
hygiene
departure
children
special_needs
```

### Prototype Phrases

Defined in `INTENT_PROTOTYPES` in `hub/retrieval/intent.py`. Examples:

- `food`: "where is food", "meal times", "food schedule", "meal distribution"
- `medical`: "I need a doctor", "medical help", "first aid"
- `registration`: "how do I register", "check in", "intake"
- `facilities`: "bathroom", "laundry", "charging station", "wi-fi"
- `inventory`: "what supplies are available", "do you have water", "are there blankets"

### Intent Threshold

```
UNCLEAR_THRESHOLD = 0.30
```

If the best intent score is below this, the classifier returns `unclear`.


## Retrieval Enrichment

**File:** `hub/retrieval/search.py`

If intent is **not** `unclear` and `intent_confidence >= 0.35`, the query is **expanded** with intent keywords.
If a second intent also scores >= 0.35, both enrichment strings are appended.

```python
if intent != "unclear" and intent_confidence >= 0.35 and intent in INTENT_ENRICHMENT:
    search_query = f"{normalized_query} {INTENT_ENRICHMENT[intent]}"
# optional: append second intent enrichment if second_confidence >= 0.35
```

### Intent Enrichment Dictionary

Defined in `hub/retrieval/search.py`:

```
greeting      -> "hello greeting"
identity      -> "kiosk assistant information"
capability    -> "help information services"
small_talk    -> "thanks okay"
food          -> "food meals schedule cafeteria canteen dining eat breakfast lunch dinner snacks"
medical       -> "medical doctor nurse health clinic first aid medicine"
registration  -> "registration sign up sign-up sign in check in intake wristband id card"
sleeping      -> "sleeping beds cots rest area sleeping area dormitory"
transportation-> "bus shuttle transport ride leave departure"
safety        -> "safety emergency evacuation exit fire earthquake"
facilities    -> "bathroom restroom showers laundry charging wifi toilet"
lost_person   -> "lost missing family reunification missing person"
pets          -> "pets dog cat animal pet area"
donations     -> "donate donations donation drop off"
hours         -> "hours open close schedule opening closing time"
location      -> "address location directions building map"
goodbye       -> "goodbye bye thanks"
inventory     -> "supply stock available items request availability"
mental_health -> "counseling stress trauma emotional mental psychological anxiety support"
legal_docs    -> "id documents legal aid certificate records assistance identification"
financial_aid -> "vouchers cash aid assistance money financial relief fund"
hygiene       -> "soap shampoo toothbrush hygiene sanitation feminine products diapers clean"
departure     -> "leave go home shelter policy duration how long stay exit"
children      -> "children daycare school child baby infant kids family welfare"
special_needs -> "wheelchair elderly disabled assistance mobility hearing impaired"
```


## Clarification Gating

**File:** `hub/retrieval/search.py`

Clarification is only triggered when:

- `intent == "unclear"` **and**
- best retrieval score `< CLARIFICATION_FLOOR`
- no valid compound pair is active

Additional guardrails:

- If intent confidence is >= 0.35, clarification is suppressed.
- If intent is one of `greeting`, `identity`, `capability`, `small_talk`, `goodbye`, clarification is suppressed.

```python
def needs_clarification(query, top_k, intent, intent_conf):
    if intent != "unclear" and intent_conf >= 0.35:
        return False
    if intent in ("greeting", "identity", "capability", "small_talk", "goodbye"):
        return False
    best_score = top_k[0].score if top_k else 0.0
    return intent == "unclear" and best_score < CLARIFICATION_FLOOR
```

## Follow-Up Auto-Answer (Intent v2.1)

When compound mode is active and the hub can still return a strong single article answer, it also emits:

- `follow_up_prompt`
- `follow_up_intent`

The kiosk stores that follow-up context for **one next user turn only**.

- If next user input is an agreement phrase (`yes`, `yes please`, `opo`, `sige`, etc., including localized sets), kiosk automatically requests retrieval for the secondary intent.
- If next user input is not an agreement, follow-up context is cleared and query is handled normally.
- The follow-up context expires after that one turn.

This preserves one-article responses while still covering mixed-intent questions.

## Emergency Disambiguation (Kiosk Guard)

Emergency auto-trigger no longer uses generic informational "help" terms by themselves.

- Explicit critical emergency phrases still trigger emergency flow.
- Tier-2 emergency keywords still use confirmation flow.
- Informational medical/location questions (for example: "Help, where is the doctor?") stay in normal Q&A unless critical emergency terms are also present.


## Clarification Category Mapping

When a user selects a clarification category, the hub maps that label to an intent
key before retry enrichment. This prevents human-readable labels (e.g. "Food & Water")
from missing enrichment.

Mapping lives in `hub/retrieval/search.py` as `CLARIFICATION_CATEGORY_TO_INTENT` and
includes entries such as:

- `Food & Water` -> `food`
- `Medical` -> `medical`
- `Registration` -> `registration`
- `Mental Health` -> `mental_health`
- `Legal Docs` -> `legal_docs`
- `Financial Aid` -> `financial_aid`
- `Hygiene` -> `hygiene`
- `Departure` -> `departure`
- `Children` -> `children`
- `Special Needs` -> `special_needs`


## Short-Circuit Intents (No KB Lookup)

If intent is **not** `unclear` and `intent_confidence >= 0.35`, some intents return
static responses without hitting the KB:

- `greeting`
- `identity`
- `capability`
- `small_talk`
- `goodbye`

These responses are defined inline in `hub/retrieval/search.py`.


## Inventory Shortcut

Before intent classification, the system checks for inventory-related phrases in
the query and returns a direct answer using shelter config (if applicable).

**Files:**
- `hub/retrieval/search.py` (invokes inventory check)
- `hub/retrieval/inventory.py` (rule-based matcher)
- `hub/db/evac_sync.py` (evac info -> KB sync)


## Normalization

**File:** `hub/retrieval/normalizer.py`

Normalization is applied before intent and embedding:

- Lowercase + trim
- Collapse whitespace
- Remove duplicate words
- Apply language-specific synonyms for `es/de/fr/ja`
- Apply English domain corrections and misspellings

This is a critical step: intent classification and retrieval work on the
normalized query string.


## Thresholds and Tunables (Environment)

These are the main config values used in retrieval and classification:

### Intent Classification

- `UNCLEAR_THRESHOLD = 0.30` (in `hub/retrieval/intent.py`)
  - If intent score < threshold, intent becomes `unclear`.
- `INTENT_ACTION_THRESHOLD = 0.35` (in `hub/retrieval/search.py`)
  - Used for enrichment, short-circuiting, and clarification suppression.

### Retrieval Thresholds

**File:** `hub/retrieval/search.py`

- `RESKIOSK_SIM_THRESHOLD` (default `0.60`)
  - English direct-match threshold.
- `RESKIOSK_CLARIFICATION_FLOOR` (default `0.40`)
  - English clarification threshold.
- `RESKIOSK_NON_EN_SIM_THRESHOLD` (default `0.50`)
  - Non-English direct-match threshold.
- `RESKIOSK_NON_EN_CLARIFICATION_FLOOR` (default `0.38`)
  - Non-English clarification threshold.
- `RESKIOSK_COMPOUND_INTENT_MIN` (default `0.35`)
  - Minimum confidence for both top intents before compound mode is considered.
- `RESKIOSK_COMPOUND_GAP_MAX` (default `0.08`)
  - Maximum allowed confidence gap between top-1 and top-2 intents for compound mode.

### RLHF / Bias Tuning

**File:** `hub/retrieval/search.py`

- `RESKIOSK_RLHF_ENABLED` (default `false`)
- `RESKIOSK_RLHF_ALPHA` (default `0.10`)
- `RESKIOSK_RLHF_BIAS_TTL_SECS` (default `1800`)


## Startup Wiring

**File:** `hub/main.py`

On startup:

- The embedder is loaded and warmed.
- An `IntentClassifier` is created using the embedder.
- The classifier is registered via `search.set_intent_classifier(...)`.


## Runtime Logging

Intent score and selected intent are logged per query:

```
[Retrieve] intent=<intent> confidence=<score>
```

These logs appear in `hub.log` and the console log stream.


## Known Behavior Notes

- If the intent classifier is unavailable (embedder failed), intent defaults to `unclear`.
- Intent enrichment only happens when confidence >= 0.35.
- Clarification is suppressed when intent is known with confidence >= 0.35.
- Normalization changes can shift intent classification outcomes because it runs before classification.
- `general_info` is intentionally not enriched to avoid adding noisy generic keywords.
- `inventory` enrichment avoids food/meal terms to reduce overlap with `food` intent.
- Clarification retries map category labels to intent keys before enrichment.

## Cloud Boundary (Currently Disabled)

Cloud integration is currently disabled. Intent/classification logic remains fully local:
- Classifier, normalization, embeddings, retrieval, and rewriter are unchanged.
