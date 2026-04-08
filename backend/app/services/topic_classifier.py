"""
Question Topic Classifier

Simple keyword-based topic classification for search queries (MVP).
Classifies into medical specialties and wellness categories.
Powers the "trending topics" view in the BI dashboard.
"""

import logging

logger = logging.getLogger(__name__)

# Keyword-based topic definitions
# A query can match multiple topics if it contains keywords from multiple categories
TOPIC_KEYWORDS = {
    "cardiovascular": [
        "heart", "cardiac", "coronary", "arrhythmia", "hypertension",
        "blood pressure", "atherosclerosis", "stroke", "angina",
        "myocardial infarction", "heart attack", "valve", "aorta",
        "ventricular", "pericarditis", "endocarditis", "myocarditis",
        "heart failure", "cardiomyopathy", "flutter", "fibrillation",
    ],
    "oncology": [
        "cancer", "tumor", "malignant", "benign", "carcinoma",
        "lymphoma", "leukemia", "melanoma", "sarcoma", "chemotherapy",
        "radiation", "oncology", "metastasis", "remission", "biopsy",
        "mammography", "colonoscopy", "polyp", "staging", "prognosis",
    ],
    "neurology": [
        "brain", "neuron", "neurology", "neurological", "neurologist",
        "alzheimer", "parkinson", "epilepsy", "seizure", "migraine",
        "headache", "concussion", "stroke", "coma", "aneurysm",
        "spinal cord", "nerve", "neuropathy", "tremor", "palsy",
        "dementia", "cognitive", "encephalitis", "meningitis",
    ],
    "infectious_disease": [
        "infection", "infectious", "bacteria", "viral", "virus",
        "pathogen", "antibiotic", "antiviral", "immune", "covid",
        "pneumonia", "flu", "influenza", "tuberculosis", "hiv",
        "hepatitis", "sepsis", "meningitis", "vaccine", "immunization",
        "communicable", "contagious", "endemic",
    ],
    "mental_health": [
        "depression", "anxiety", "panic", "bipolar", "schizophrenia",
        "psychosis", "mental health", "psychiatry", "psychiatric",
        "ptsd", "trauma", "ocd", "obsessive", "compulsive",
        "eating disorder", "bulimia", "anorexia", "suicidal",
        "antidepressant", "psychotherapy", "cognitive behavioral",
        "stress", "phobia", "autism", "adhd", "attention deficit",
    ],
    "pediatrics": [
        "child", "children", "pediatric", "pediatrics", "infant",
        "baby", "newborn", "toddler", "adolescent", "teenager",
        "childhood", "development", "growth", "vaccination",
        "immunization", "congenital", "colic", "teething",
        "autism spectrum", "cerebral palsy",
    ],
    "orthopedics": [
        "bone", "fracture", "orthopedic", "joint", "ligament",
        "tendon", "muscle", "arthritis", "osteoarthritis", "arthroscopy",
        "sprain", "strain", "dislocation", "knee", "hip", "shoulder",
        "back", "spine", "vertebra", "disk", "osteoporosis",
        "replacement", "prosthetic", "cast", "brace",
    ],
    "dermatology": [
        "skin", "dermatology", "dermatologist", "rash", "dermatitis",
        "eczema", "psoriasis", "acne", "mole", "melanoma",
        "fungal", "bacterial", "wart", "herpes", "shingles",
        "hives", "urticaria", "lichen", "scabies", "lice",
        "sunburn", "scar", "burn", "wound", "tattoo",
    ],
    "endocrinology": [
        "diabetes", "thyroid", "hormone", "endocrine", "endocrinology",
        "insulin", "glucose", "metabolism", "metabolic",
        "hypothyroidism", "hyperthyroidism", "adrenal", "pituitary",
        "estrogen", "testosterone", "cortisol", "obesity",
        "thyroiditis", "graves", "hashimoto", "pancreas",
    ],
    "respiratory": [
        "lung", "respiratory", "asthma", "copd", "pneumonia",
        "bronchitis", "emphysema", "pulmonary", "oxygen",
        "breathing", "cough", "wheeze", "dyspnea", "shortness of breath",
        "tuberculosis", "influenza", "covid", "bronchial",
        "trachea", "larynx", "pleura", "diaphragm",
    ],
    "gastroenterology": [
        "stomach", "gastric", "gastrointestinal", "gi", "bowel",
        "intestine", "colon", "ulcer", "gastritis", "colitis",
        "ibd", "crohn", "ulcerative colitis", "celiac", "gluten",
        "ibs", "irritable", "acid reflux", "gerd", "heartburn",
        "liver", "hepatitis", "cirrhosis", "pancreas", "appendix",
    ],
    "alternative_medicine": [
        "herbal", "herb", "acupuncture", "acupressure", "homeopathy",
        "naturopathy", "ayurveda", "traditional medicine",
        "chinese medicine", "tcm", "supplement", "natural remedy",
        "essential oil", "aromatherapy", "meditation", "yoga",
        "chiropractic", "osteopathy", "naturopath", "holistic",
    ],
    "fitness_wellness": [
        "exercise", "fitness", "workout", "training", "strength",
        "cardio", "aerobic", "stretching", "flexibility", "gym",
        "wellness", "health", "fitness", "wellbeing", "exercise",
        "running", "walking", "cycling", "swimming", "yoga",
        "pilates", "tai chi", "physical therapy", "rehabilitation",
    ],
    "nutrition": [
        "nutrition", "diet", "nutrient", "vitamin", "mineral",
        "protein", "carbohydrate", "fat", "calorie", "meal plan",
        "food", "eating", "supplement", "supplement", "mineral",
        "antioxidant", "fiber", "sodium", "sugar", "cholesterol",
        "organic", "vegan", "vegetarian", "paleo", "keto",
    ],
    "general": [
        "health", "healthcare", "disease", "medical", "treatment",
        "medication", "cure", "prevention", "diagnosis", "doctor",
        "hospital", "clinic", "patient", "therapy", "wellness",
    ],
}

# Pre-compute lowercase keyword sets for faster matching
_LOWERCASE_TOPICS = {
    topic: set(kw.lower() for kw in keywords)
    for topic, keywords in TOPIC_KEYWORDS.items()
}


def classify_query_topic(query: str) -> list[str]:
    """
    Classify a search query into one or more topic categories.

    Args:
        query: The user's search query

    Returns:
        List of matching topic categories (can be empty or multiple)
    """
    if not query or not query.strip():
        return []

    # Normalize query for matching
    query_lower = query.lower()
    # Remove common punctuation for better matching
    query_normalized = query_lower.replace("?", "").replace("!", "")

    matched_topics = []

    # Check each topic's keywords
    for topic, keywords in _LOWERCASE_TOPICS.items():
        # Match if any keyword appears as a word in the query
        for keyword in keywords:
            if keyword in query_normalized:
                matched_topics.append(topic)
                break  # Found a match for this topic, move to next

    logger.debug(f"Classified query '{query}' to topics: {matched_topics}")

    # Always include 'general' if nothing else matched
    if not matched_topics:
        matched_topics.append("general")

    return matched_topics
