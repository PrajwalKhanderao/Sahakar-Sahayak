import json
import random
import string
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from knowledge_base import FAQKnowledgeBase 
from translate_utils import (
    CURATED_LANGUAGES,
    SUPPORTED_LANGUAGES,
    detect_language,
    from_english,
    to_english,
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
GRIEVANCES_PATH = Path(__file__).parent / "data" / "grievances.json"

app = FastAPI(title="Cooperative Governance & Legal Assistance Chatbot")

# Wide-open CORS for local prototyping. Tighten this before deploying
# anywhere beyond your own machine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

kb = FAQKnowledgeBase()


class ChatRequest(BaseModel):
    message: str
    # "auto" detects the reply language from the message; otherwise pass an
    # explicit code from SUPPORTED_LANGUAGES (e.g. the user picked one in the UI).
    lang: str = "auto"


class ChatResponse(BaseModel):
    reply: str
    category: str | None
    detected_lang: str
    confidence: float
    is_machine_translated: bool
    matched_question: str | None


DISCLAIMER = {
    "en": "This is general information, not legal advice for your specific situation. For binding advice, consult your state Registrar of Cooperative Societies or a lawyer.",
    "hi": "यह सामान्य जानकारी है, आपकी विशिष्ट स्थिति के लिए कानूनी सलाह नहीं। बाध्यकारी सलाह हेतु अपने राज्य सहकारी सोसाइटी रजिस्ट्रार या वकील से संपर्क करें।",
    "mr": "ही सर्वसाधारण माहिती आहे, तुमच्या विशिष्ट परिस्थितीसाठी कायदेशीर सल्ला नाही. बंधनकारक सल्ल्यासाठी तुमच्या राज्याच्या सहकारी संस्था निबंधकांशी किंवा वकिलाशी संपर्क साधा.",
}

class GrievanceRequest(BaseModel):
    category: str
    description: str
    contact: str | None = None
    lang: str = "en"


class GrievanceResponse(BaseModel):
    reference_id: str
    message: str


GRIEVANCE_CATEGORIES = [
    "Loan / credit dispute",
    "Committee conduct / transparency",
    "Election-related",
    "PMFBY / crop insurance claim delay",
    "PACS service issue",
    "Other",
]

GRIEVANCE_ACK = {
    "en": "Your grievance has been logged. Reference ID: {ref}. Please save this for follow-up — you can quote it when contacting your society or the Registrar's office.",
    "hi": "आपकी शिकायत दर्ज कर ली गई है। संदर्भ आईडी: {ref}। कृपया अनुवर्ती कार्रवाई के लिए इसे सुरक्षित रखें — अपनी सोसाइटी या रजिस्ट्रार कार्यालय से संपर्क करते समय आप इसका उल्लेख कर सकते हैं।",
    "mr": "तुमची तक्रार नोंदवली गेली आहे. संदर्भ आयडी: {ref}. कृपया पाठपुराव्यासाठी हे जपून ठेवा — तुमच्या संस्थेशी किंवा निबंधक कार्यालयाशी संपर्क साधताना तुम्ही याचा उल्लेख करू शकता.",
}


def _load_grievances() -> list:
    if not GRIEVANCES_PATH.exists():
        return []
    with open(GRIEVANCES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_grievances(records: list) -> None:
    GRIEVANCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GRIEVANCES_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def _generate_reference_id() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"GRV-{date_part}-{rand_part}"


FALLBACK_REPLY_EN = (
    "I don't have a confident answer for that yet in my knowledge base. "
    "Try rephrasing, or ask about registration, bylaws, elections, audits, "
    "member disputes, loans/credit, dissolution, or membership rights."
)


@app.get("/api/categories")
def get_categories():
    return {"categories": kb.categories(), "languages": SUPPORTED_LANGUAGES}


@app.get("/api/grievance/categories")
def get_grievance_categories():
    return {"categories": GRIEVANCE_CATEGORIES}


@app.post("/api/grievance", response_model=GrievanceResponse)
def file_grievance(req: GrievanceRequest):
    reference_id = _generate_reference_id()
    records = _load_grievances()
    records.append(
        {
            "reference_id": reference_id,
            "category": req.category,
            "description": req.description,
            "contact": req.contact,
            "lang": req.lang,
            "filed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _save_grievances(records)

    ack = GRIEVANCE_ACK.get(req.lang, GRIEVANCE_ACK["en"]).format(ref=reference_id)
    return GrievanceResponse(reference_id=reference_id, message=ack)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    user_lang = req.lang
    if user_lang == "auto" or user_lang not in SUPPORTED_LANGUAGES:
        user_lang = detect_language(req.message)

    query_en = to_english(req.message, user_lang)
    faq, score = kb.best_match(query_en)

    if faq is None:
        reply_en = FALLBACK_REPLY_EN
        category = None
        matched_question = None
        is_machine_translated = user_lang != "en"
        reply = from_english(reply_en, user_lang) if user_lang != "en" else reply_en
    else:
        category = faq["category"]
        matched_question = faq["question_en"]
        if user_lang in faq["answers"]:
            reply = faq["answers"][user_lang]
            is_machine_translated = False
        else:
            reply = from_english(faq["answers"]["en"], user_lang)
            is_machine_translated = True

    disclaimer = DISCLAIMER.get(user_lang, DISCLAIMER["en"])
    reply = f"{reply}\n\n{disclaimer}"

    return ChatResponse(
        reply=reply,
        category=category,
        detected_lang=user_lang,
        confidence=round(float(score), 3),
        is_machine_translated=is_machine_translated,
        matched_question=matched_question,
    )


# Serve the chat UI itself at "/", and any static assets under /static.
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")
