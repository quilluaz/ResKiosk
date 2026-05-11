"""
Prototype-based intent classifier using the same MiniLM embedder as semantic search.
Used to enrich queries before retrieval and to gate clarification (only when intent is unclear).
"""
import numpy as np
from typing import Tuple, List, Dict

# Intent labels for evacuation-center kiosk (excluding "unclear", which is returned when confidence < 0.30)
INTENT_LABELS: List[str] = [
    "greeting",
    "identity",
    "capability",
    "small_talk",
    "food",
    "medical",
    "registration",
    "sleeping",
    "transportation",
    "safety",
    "facilities",
    "lost_person",
    "pets",
    "donations",
    "hours",
    "location",
    "general_info",
    "goodbye",
    "inventory",
    "mental_health",
    "legal_docs",
    "financial_aid",
    "hygiene",
    "departure",
    "children",
    "special_needs",
]

INTENT_PROTOTYPES: Dict[str, List[str]] = {
    "greeting": [
        "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
        "howdy", "hi there", "hello there", "greetings", "hey there",
        "good day", "morning", "evening",
    ],
    "identity": [
        "who are you", "what are you", "what is this", "what is this kiosk",
        "are you a robot", "are you human", "what is reskiosk",
        "what is this place", "what is this screen",
    ],
    "capability": [
        "what can you do", "what can you help with", "how can you help",
        "what information do you have", "what do you know", "can you help me",
        "what can i ask", "what can i say", "what services do you have",
    ],
    "small_talk": [
        "how are you", "how is it going", "nice day", "thank you", "thanks",
        "okay", "alright", "got it", "i see", "appreciate it",
        "great", "cool", "okay thanks",
    ],
    "food": [
        "where is food", "when is lunch", "when is dinner", "meal times",
        "where do we eat", "food schedule", "breakfast hours", "where can i get food",
        "is there food", "meal distribution", "feeding times", "cafeteria",
        "food", "hungry", "food please", "eat where", "meal today",
        "where eat", "can i eat", "meal time",
        "where po food", "food po", "ate where food", "sir where food", "maam where food",
    ],
    "medical": [
        "i need a doctor", "medical help", "where is the nurse", "i feel sick",
        "medical assistance", "first aid", "where is medical", "health services",
        "i need medicine", "medical tent", "doctor", "nurse",
        "hurt bad", "injury", "bleeding", "burn", "fever",
        "help im sick", "medical", "clinic",
    ],
    "registration": [
        "how do i register", "where do i sign in", "registration desk",
        "check in", "sign up", "register my family", "registration process",
        "where to register", "get registered", "intake",
        "register", "sign in", "check-in", "registration",
        "id check", "wristband",
        "where po register", "register po", "can i po register", "sir register", "maam register",
    ],
    "sleeping": [
        "where do i sleep", "sleeping area", "where can i sleep", "beds",
        "sleeping quarters", "cots", "rest area", "where to sleep",
        "sleeping arrangements", "overnight",
        "sleep", "sleeping", "bed", "cot",
        "i need to sleep", "where can i lie down",
    ],
    "transportation": [
        "how do i leave", "bus schedule", "when is the bus", "transportation",
        "ride", "shuttle", "how to get out", "when can i leave",
        "bus to town", "transport", "pickup",
        "ride out", "bus", "shuttle time", "transport help",
    ],
    "safety": [
        "is it safe", "emergency", "evacuation", "where to go in emergency",
        "safety", "fire exit", "emergency exit", "what if there is a fire",
        "danger", "unsafe", "hazard", "earthquake", "flood", "storm",
    ],
    "facilities": [
        "where is the bathroom", "restroom", "toilet", "showers",
        "laundry", "charging station", "phone charging", "wi-fi",
        "bathroom", "washroom", "where can i shower",
        "wifi", "internet", "charging", "laundry area", "shower",
    ],
    "lost_person": [
        "i lost my family", "missing person", "lost my child", "find my family",
        "reunification", "lost and found", "where is my husband", "missing child",
        "family lost", "lost person", "where is my wife",
    ],
    "pets": [
        "can i bring my dog", "pets allowed", "where do i put my pet",
        "animal", "dog", "cat", "pet area", "pet shelter",
        "pet", "pet help",
    ],
    "donations": [
        "where do i donate", "how to donate", "donation center",
        "i want to donate", "accepting donations", "drop off donations",
        "donate", "donations", "donation drop off",
    ],
    "hours": [
        "what time do you open", "when do you close", "hours of operation",
        "opening hours", "when is the desk open", "what time",
        "hours", "open time", "close time", "opening time", "closing time",
    ],
    "location": [
        "where am i", "address", "where is this place", "how do i get here",
        "directions", "what is this building", "where is the center",
        "location", "map", "where are we",
    ],
    "general_info": [
        "what services are available", "what do you offer", "general information",
        "tell me about the center", "what is available", "help",
        "i need help", "i have a question", "information",
        "i dont know what to do", "please help", "need help now",
        "can i po ask", "where po", "sir can i ask", "maam can i ask",
    ],
    "goodbye": [
        "bye", "goodbye", "see you", "thank you goodbye", "thats all",
        "nothing else", "done", "thats it", "im done",
    ],
    "inventory": [
        "what supplies are available", "is there food", "do you have water",
        "are there blankets available", "what do you have here",
        "is medicine available", "are there hygiene kits", "inventory status",
        "is there clothing", "are there diapers", "are charging ports available",
        "are there cots", "what can i get", "supply levels", "what is available",
        "may pagkain ba", "may gamot ba", "may tubig ba",
        "hay comida", "hay agua", "hay medicamentos",
        "supplies", "supplies available",
    ],
    "mental_health": [
        "stress", "anxiety", "panic", "i feel scared", "i feel afraid",
        "i need to talk", "counseling", "counselor", "mental health",
        "emotional support", "trauma", "i cant sleep", "im overwhelmed",
        "i need support", "help with stress", "fear", "worried",
    ],
    "legal_docs": [
        "legal aid", "legal help", "lawyer", "id replacement", "lost id",
        "documents", "paperwork", "certificate", "records",
        "identification", "id", "birth certificate", "police report",
        "legal documents", "replace id", "missing documents",
    ],
    "financial_aid": [
        "financial aid", "cash aid", "vouchers", "money help", "relief fund",
        "assistance money", "cash assistance", "financial help", "aid money",
        "cash support", "financial relief", "voucher", "funding",
        "can i get money", "help with money",
    ],
    "hygiene": [
        "soap", "shampoo", "toothbrush", "toothpaste", "hygiene",
        "sanitation", "feminine products", "pads", "tampons",
        "diapers", "wipes", "clean", "toiletries", "hygiene kits",
        "need soap", "need diapers",
    ],
    "departure": [
        "when can i leave", "can i leave today", "go home", "leaving",
        "exit policy", "how long can i stay", "duration", "shelter policy",
        "how long stay", "when do we leave", "can i go home",
        "departure", "leave", "stay length", "check out",
    ],
    "children": [
        "child care", "childcare", "daycare", "kids", "children",
        "baby", "infant", "school", "kids area", "child services",
        "family services", "where is my child", "help with baby",
        "milk for baby", "baby care",
    ],
    "special_needs": [
        "wheelchair", "elderly", "disabled", "disability", "mobility",
        "hearing impaired", "vision impaired", "special needs",
        "accessibility", "ramp", "assistive", "care for elderly",
        "medical device", "oxygen", "mobility help",
    ],
}

UNCLEAR_THRESHOLD = 0.30


class IntentClassifier:
    """
    Classifies user queries into one of INTENT_LABELS using prototype phrase embeddings.
    Centroids are computed at init; classify() returns (intent, score), or ("unclear", score) if best_score < 0.30.
    """

    def __init__(self, embedder):
        self.embedder = embedder
        self._centroids: Dict[str, np.ndarray] = {}
        self._build_centroids()

    def _build_centroids(self) -> None:
        all_phrases = []
        intent_index = []  # which intent each phrase belongs to
        for intent in INTENT_LABELS:
            phrases = INTENT_PROTOTYPES.get(intent, [])
            for _ in phrases:
                intent_index.append(intent)
            all_phrases.extend(phrases)

        if not all_phrases:
            return

        # Batch embed all prototypes
        embeddings = self.embedder.embed_text(all_phrases)
        if isinstance(embeddings, np.ndarray) and embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        # Average per intent and L2-normalize
        for intent in INTENT_LABELS:
            indices = [i for i, intent_name in enumerate(intent_index) if intent_name == intent]
            if not indices:
                continue
            vecs = embeddings[indices]
            centroid = np.mean(vecs, axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            self._centroids[intent] = centroid.astype(np.float32)

    def classify(self, query: str) -> Tuple[str, float]:
        """
        Returns (best_intent, best_score). If best_score < UNCLEAR_THRESHOLD, returns ("unclear", best_score).
        """
        if not self._centroids:
            return ("unclear", 0.0)

        q_vec = self.embedder.embed_text(query.strip())
        if isinstance(q_vec, np.ndarray) and q_vec.ndim > 1:
            q_vec = q_vec[0]
        q_norm = np.linalg.norm(q_vec)
        if q_norm <= 0:
            return ("unclear", 0.0)
        q_vec = (q_vec / q_norm).astype(np.float32)

        best_intent = "unclear"
        best_score = -1.0
        for intent, centroid in self._centroids.items():
            score = float(np.dot(q_vec, centroid))
            if score > best_score:
                best_score = score
                best_intent = intent

        if best_score < UNCLEAR_THRESHOLD:
            return ("unclear", best_score)
        return (best_intent, best_score)

    def classify_top2(self, query: str) -> Tuple[str, float, str | None, float]:
        """
        Returns (best_intent, best_score, second_intent, second_score).
        If best_score < UNCLEAR_THRESHOLD, best_intent becomes "unclear".
        """
        if not self._centroids:
            return ("unclear", 0.0, None, 0.0)

        q_vec = self.embedder.embed_text(query.strip())
        if isinstance(q_vec, np.ndarray) and q_vec.ndim > 1:
            q_vec = q_vec[0]
        q_norm = np.linalg.norm(q_vec)
        if q_norm <= 0:
            return ("unclear", 0.0, None, 0.0)
        q_vec = (q_vec / q_norm).astype(np.float32)

        scores = []
        for intent, centroid in self._centroids.items():
            score = float(np.dot(q_vec, centroid))
            scores.append((intent, score))
        scores.sort(key=lambda x: x[1], reverse=True)

        best_intent, best_score = scores[0]
        second_intent, second_score = (scores[1] if len(scores) > 1 else (None, 0.0))

        if best_score < UNCLEAR_THRESHOLD:
            return ("unclear", best_score, second_intent, second_score)
        return (best_intent, best_score, second_intent, second_score)
