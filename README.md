# Sahakar Sahayak — Multilingual Cooperative Governance & Legal Assistance Chatbot

A working prototype of a chatbot that answers cooperative-society governance
and legal questions — registration, bylaws, elections, audits, disputes,
loans, dissolution, membership rights, **PMFBY crop insurance, Ministry of
Cooperation schemes, financial literacy, and grievance redressal** — in the
user's own language, with voice input/output for low-literacy rural users.

Built against SIH Problem Statement **26088** (Ministry of Cooperation / NCCT):
*Multilingual Cooperative Governance & Legal Assistance Chatbot*.

## Stack (and why)

- **FastAPI** (Python) — small, fast to iterate on, great for a hackathon-speed backend.
- **scikit-learn TF-IDF + cosine similarity** — a real, working retrieval engine
  with *zero* API keys or cost. It matches a question to the right FAQ entry
  from a curated knowledge base. No LLM required to get something useful running today.
- **langdetect** — detects the language of what the user typed (offline, no API key).
- **deep-translator (Google Translate wrapper)** — translates the query to English
  for matching, and translates answers into languages we haven't hand-written yet.
  Needs internet at request time, but no API key.
- **Plain HTML/CSS/JS frontend** — no build step, one file, easy to hand off to a
  designer or swap into React later.
- **Web Speech API** (`SpeechRecognition` + `SpeechSynthesis`) — voice input and
  read-aloud replies, built into the browser, no external STT/TTS service or
  API key needed for the prototype. Works in Chrome; gracefully disables the
  mic button in browsers that don't support it.

### Why retrieval instead of an LLM?
For governance/legal content, you want answers that are *traceable to a
specific, reviewed source* — not generated fresh each time, which risks
confidently-wrong "hallucinated" legal claims. This prototype answers only
from a curated knowledge base and tells you its confidence score. Swap in an
LLM later for phrasing/summarization on top of retrieved facts (see below),
not for inventing facts.

## Project structure

```
coop-legal-bot/
  backend/
    main.py              # FastAPI app: /api/chat, /api/categories, serves the UI
    knowledge_base.py     # TF-IDF retrieval over the FAQ data
    translate_utils.py    # language detection + translation helpers
    data/faqs.json         # the knowledge base — 20 FAQs across 12 categories
                           # (incl. PMFBY, Ministry schemes, financial literacy,
                           # grievance redressal), each hand-written in
                           # English, Hindi, and Marathi
    data/grievances.json  # grievances filed through the app land here (demo storage)
    requirements.txt
  frontend/
    index.html            # single-file chat UI (no build step)
  README.md
```

## How to run it

1. **Install dependencies** (Python 3.10+ recommended):
   ```bash
   cd coop-legal-bot/backend
   pip install -r requirements.txt
   ```

2. **Start the server** (from the `coop-legal-bot` folder, one level up from `backend/`):
   ```bash
   cd ..
   uvicorn backend.main:app --reload --port 8000
   ```

3. **Open the app**: go to `http://localhost:8000` in your browser. That's it —
   FastAPI serves the frontend directly, so there's no separate frontend server.

4. Try asking (in the UI):
   - "How do we register a new cooperative society?"
   - "उपनियम कैसे संशोधित करें?" (Hindi: how to amend bylaws)
   - "PMFBY मध्ये कसे नोंदणी करावी?" (Marathi: how to enroll in PMFBY)
   - "What is PACS computerization?"
   - Something unrelated, like "what's the weather today" — it should say it
     doesn't have a confident answer, rather than making one up.

Each reply shows its detected language, matched category, and a match-confidence
percentage, so you can see exactly how the retrieval made its decision.

5. **Voice input**: click the 🎙 mic button, allow microphone access when
   Chrome prompts you, and speak your question — it fills the text box, then
   press Ask (or it's ready to submit). Voice recognition uses whatever
   language is selected in the sidebar dropdown (pick a specific language
   first — auto-detect doesn't work for voice input since the browser needs
   to know which language to listen for).

6. **Voice output**: tick "🔊 Read replies aloud" and the bot will speak each
   answer using the browser's built-in text-to-speech, in the reply's language.

7. **File a Grievance**: click "File a Grievance" in the sidebar, pick a
   category, describe the issue, and submit. You'll get a tracking reference
   (e.g. `GRV-20260907-A1B2`) instantly. Filed grievances are saved to
   `backend/data/grievances.json` — open that file to see them accumulate as
   you test, or to demo "here's where a real backend would pick this up."

## What's still worth building (updated against PS 26088)

- **Mobile app / PWA wrapper** — PS calls for mobile + web integration; the
  backend already serves a clean JSON API, so a React Native or Flutter
  client (or just making the current page an installable PWA) is additive,
  not a rewrite.
- **Cloud deployment** — deploy the FastAPI backend to Render/Railway/AWS and
  point the frontend at it, so you have a live URL for demo day rather than
  "runs on my laptop."
- **Real STT/TTS for feature phones or offline use** — the Web Speech API
  needs a modern browser and internet; for a genuinely rural/low-connectivity
  audience, an IVR/SMS/USSD channel or an on-device STT model (e.g. Bhashini,
  India's own multilingual AI stack) would be the production answer.

## What I'd extend first

1. **Grow the knowledge base, and make it per-state.** Cooperative law in
   India is largely a *state subject* (each state has its own Cooperative
   Societies Act, plus the Multi-State Cooperative Societies Act 2002 for
   multi-state cooperatives). Right now the answers are deliberately generic.
   Add a `state` field to each FAQ and a state picker in the UI, and load the
   right variant — this is the single highest-value change for a real SIH
   demo, since judges will likely test it against their own state's rules.

2. **Add more languages properly.** Only English/Hindi/Marathi are
   hand-written and reviewed; everything else falls back to machine
   translation (flagged as `is_machine_translated` in the API response —
   the UI already surfaces this). For a legal-assistance bot, mistranslation
   risk matters. Prioritize getting a native speaker or a reviewed MT pass
   for 2-3 more major languages (Bengali, Tamil, Telugu, Gujarati) rather
   than relying on live machine translation for all of them.

3. **Swap keyword/TF-IDF retrieval for embeddings, and add an LLM
   answer-composer on top.** TF-IDF gets you far for a fixed FAQ set, but it
   won't handle paraphrased or multi-part questions well. A good next step:
   embed the FAQ corpus with a multilingual embedding model (e.g.
   `sentence-transformers` multilingual models, or an API-based embedding),
   and — critically — feed the *retrieved* FAQ text into an LLM only to
   rephrase/combine it conversationally, with instructions never to add facts
   not present in the retrieved context. That keeps the traceability property
   while making the bot feel much smarter.

4. **Persist conversations + escalation path.** Add a database (SQLite is
   fine to start) to log queries, especially the ones that fall below the
   confidence threshold — that log is a ready-made backlog of new FAQs to
   write. Also add a "connect me to a human" escalation for anything
   legally consequential (disputes, loan defaults) rather than letting the
   bot be the last word.

5. **WhatsApp/SMS delivery.** Most cooperative members you're targeting may
   not use a web app. Wiring this FastAPI backend behind the WhatsApp
   Business API (or even a basic SMS gateway) would massively widen reach —
   the `/api/chat` endpoint is already decoupled from the UI, so this is a
   new "frontend" rather than a backend rewrite.

## Known limitations (be upfront about these in a demo)

- Answers are informational, not legal advice — the UI shows this disclaimer
  on every reply.
- Only 12 seed FAQs across 8 categories — enough to demo the mechanism, not
  a production knowledge base.
- Machine-translated replies (anything outside English/Hindi/Marathi) are
  not legally reviewed.
- `langdetect` is unreliable on very short inputs (e.g. single words) — the
  language picker lets users override auto-detection for exactly this reason.
