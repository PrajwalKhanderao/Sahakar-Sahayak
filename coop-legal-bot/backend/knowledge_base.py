"""
Simple retrieval layer over the cooperative-governance FAQ knowledge base.

Approach: TF-IDF + cosine similarity over each FAQ's English question and
keywords. This is intentionally lightweight (no LLM/API key required) so the
prototype runs fully offline once dependencies are installed. Swap this out
for a real embeddings-based retriever or an LLM call as a first extension —
see README.md.
"""
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = Path(__file__).parent / "data" / "faqs.json"

# Below this similarity score, we treat the query as "not found" rather than
# forcing a confident-looking but wrong answer.
CONFIDENCE_THRESHOLD = 0.12


class FAQKnowledgeBase:
    def __init__(self, data_path: Path = DATA_PATH):
        with open(data_path, "r", encoding="utf-8") as f:
            self.faqs = json.load(f)

        # Build the corpus each FAQ is matched against: its English question
        # plus its keyword list, so both natural questions and short keyword
        # queries retrieve well.
        self._corpus = [
            f"{item['question_en']} {' '.join(item.get('keywords', []))}"
            for item in self.faqs
        ]
        self._vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
        self._matrix = self._vectorizer.fit_transform(self._corpus)

    def categories(self):
        seen = []
        for item in self.faqs:
            if item["category"] not in seen:
                seen.append(item["category"])
        return seen

    def search(self, query_en: str, top_k: int = 1):
        """Return the top_k best-matching FAQ entries for an English query,
        each paired with its similarity score."""
        if not query_en.strip():
            return []

        query_vec = self._vectorizer.transform([query_en])
        scores = cosine_similarity(query_vec, self._matrix)[0]

        ranked = sorted(
            zip(self.faqs, scores), key=lambda pair: pair[1], reverse=True
        )
        return ranked[:top_k]

    def best_match(self, query_en: str):
        results = self.search(query_en, top_k=1)
        if not results:
            return None, 0.0
        faq, score = results[0]
        if score < CONFIDENCE_THRESHOLD:
            return None, score
        return faq, score

    def get_by_id(self, faq_id: str):
        for item in self.faqs:
            if item["id"] == faq_id:
                return item
        return None
