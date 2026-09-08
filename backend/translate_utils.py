"""
Language detection + translation helpers.

- Detection uses `langdetect` (pure Python, offline, no API key).
- Translation uses `deep-translator`'s GoogleTranslator wrapper, which calls
  Google Translate's public endpoint. This needs internet access at request
  time but no API key. If it fails (offline, rate-limited, etc.) we fall
  back gracefully to the original text so the bot never crashes.

Supported UI languages are intentionally kept small for the prototype;
extend SUPPORTED_LANGUAGES to add more (see README "what to extend first").
"""
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "mr": "मराठी (Marathi)",
    "bn": "বাংলা (Bengali)",
    "ta": "தமிழ் (Tamil)",
    "te": "తెలుగు (Telugu)",
    "gu": "ગુજરાતી (Gujarati)",
}

CURATED_LANGUAGES = {"en", "hi", "mr"}


def detect_language(text: str) -> str:
    """Best-effort language detection; defaults to English on failure or
    very short input (langdetect is unreliable under ~3 words)."""
    try:
        code = detect(text)
    except LangDetectException:
        return "en"
    return code if code in SUPPORTED_LANGUAGES else "en"


def to_english(text: str, source_lang: str) -> str:
    if source_lang == "en":
        return text
    try:
        return GoogleTranslator(source=source_lang, target="en").translate(text)
    except Exception:
        
        return text


def from_english(text: str, target_lang: str) -> str:
    if target_lang == "en":
        return text
    try:
        return GoogleTranslator(source="en", target=target_lang).translate(text)
    except Exception:
        return text
