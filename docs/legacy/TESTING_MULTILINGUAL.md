# Multilingual STT → Hub → TTS: Testing Guide

Use this checklist for manual end-to-end testing of each supported language.  
**Supported set:** `en`, `ja`, `es`, `de`, `fr`.

**Prerequisites:**
- Hub running (e.g. **TO RUN/start_hub.vbs**; see [GET_STARTED.md](../GET_STARTED.md)).
- Kiosk and hub on same network; hub URL configured in the app.
- All required models downloaded (use **Settings → Check models & download** in the app).

---

## 1. Per-language test (repeat for en, ja, es, de, fr)

For each language:

| Step | What to do | What to check |
|------|------------|---------------|
| 1 | Set language in the app to the target language. | Language selector shows the correct language; no crash. |
| 2 | Tap **Tap to Speak**, say a short question in that language (e.g. “Where is the registration desk?” / “¿Dónde está el mostrador de registro?” / “Wo ist die Essensausgabe?” / “Où est la distribution de nourriture?” / “受付はどこですか？”). Hold at least **2 seconds** for **es/de/fr** (batch STT). | See “Preparing…” then either live transcript (en/ja) or “Listening…” (es/de/fr). No “I didn’t hear anything” if you actually spoke. |
| 3 | Release the button. | **Streaming (en/ja):** Your transcript appears and is replaced by “Asking hub…” then the answer. **Batch (es/de/fr):** “Listening…” is replaced by your transcript, then “Asking hub…”, then the answer. |
| 4 | Watch the chat and listen. | Final answer appears **in the selected language** (text in chat). TTS speaks the answer in that language. |
| 5 | (Optional) Check hub logs. | Hub receives the request with correct `language`; if non-English, you see translation to EN for search and translation back for the response. |

**Sample phrases (optional):**
- **en:** “Where is the registration desk?”
- **es:** “¿Dónde está el mostrador de registro?”
- **de:** “Wo ist die Essensausgabe?”
- **fr:** “Où est la distribution de nourriture?”
- **ja:** “受付はどこですか？” (Where is the reception desk?)

---

## 2. Streaming vs batch UX

| Language type | Languages | What you should see |
|---------------|-----------|----------------------|
| **Streaming** | en, ja | Short “Preparing…” → live transcript while you speak → on release: transcript stays, then “Asking hub…” → answer. |
| **Batch** | es, de, fr | Short “Preparing…” → **no** live transcript; “Listening…” appears only after the system confirms it’s hearing audio → on release: “Listening…” replaced by transcript, then “Asking hub…” → answer. |

If you tap and **don’t** speak (or speak too quietly), you should get **“I didn’t hear anything. Please try again.”** (or the localized equivalent) and **no** “Listening…” left in the chat.

---

## 3. Error and edge cases

| Test | Action | Expected |
|------|--------|----------|
| No speech (batch) | Select es/de/fr, tap to speak, stay silent, release after 2+ s. | No “Listening…” if no audio; then “I didn’t hear anything…” (or localized) in chat. |
| Too short (batch) | Select es/de/fr, tap, say one short syllable, release before 2 s. | “Recording was too short…” (or localized) in chat. |
| Hub unreachable | Turn off hub or disconnect network; ask a question. | Error message in chat and/or TTS (localized); app does not freeze. |
| Language switch | Mid-session, change language; then ask a question in the new language. | No crash; STT/TTS and response in the new language. |

---

## 4. TTS and translation sanity check

- **TTS:** For each of en, ja, es, de, fr, listen to the spoken answer. It should be in that language and intelligible (no wrong language, no garbled audio).
- **Translation:** For es/de/fr/ja, in hub logs (or by checking response payload), confirm the answer text returned to the kiosk is in the requested language, not English.

---

## 5. Unit tests (optional)

From project root:

```bash
cd kiosk
./gradlew test
```

Covers STT post-processing and ViewModel logic; does **not** replace the manual end-to-end flow above.

---

## 6. Documenting results

When you run the **end-to-end-language-tests** todo, record:

- **Per language:** Pass/fail for “speech → transcript → hub answer → TTS” in the correct language.
- **Streaming (en/ja):** Live transcript and “Asking hub…” behavior.
- **Batch (es/de/fr):** “Listening…” only when hearing audio; correct replacement by transcript and “Asking hub…”.
- **Errors:** Any “didn’t hear”, “too short”, or hub errors shown correctly in chat in the set language.
- **TTS:** Any language that sounds wrong or unintelligible.

You can keep this in a short table (e.g. in a comment in the plan, in this doc, or in a separate `TEST_RUN_YYYY-MM-DD.md`).
