"""Blocks diagnostic or medication wording before any text is shown."""

BLOCKED = [
    "you have", "you are suffering", "diagnos", "disease", "condition:", "take ", "dose", "medication", "prescri",
    # hedged diagnosis
    "may have", "might have", "could have", "must have", "probably have", "likely have",
    "you may be", "you might be", "you could be", "suggests", "indicates", " sign of", " signs of", "symptom",
    "consistent with", "points to", "caused by", "suffering from", "your condition", "a condition", "this condition",
    # condition names
    "insomnia", "depression", "depressed", "anxiety", "apnea", "apnoea", "anemia", "anaemia",
    "tachycardia", "bradycardia", " fever", "infection", "disorder", "illness", "burnout", "dementia",
    "hypertension", "heart attack", "concussion", "cancer", "diabet", "dehydrat",
    # medication
    "melatonin", " pill", " drug", "medicine", "ibuprofen", "paracetamol", "acetaminophen", "aspirin",
    "zolpidem", "ambien ", "modafinil", "antidepress", "sedative", "stimulant", "supplement", "painkiller", "milligram",
    " mg ", " mg.", " mg,", " treat", " cure", "therapy", "remedy",
]


def normalise(text: str) -> str:
    """Lower case, every run of whitespace one space, one space at each end (so a leading space means a word start)."""
    return " " + " ".join(text.lower().split()) + " "


def blocks_diagnostic(text: str) -> list[str]:
    normalised = normalise(text)
    return [p for p in BLOCKED if p in normalised]
