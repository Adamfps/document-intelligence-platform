import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ----------------------------
# Document type patterns
# ----------------------------

PAN_REGEX = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")  # ABCDE1234F
AADHAAR_12_DIGIT = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")  # 1234 5678 9012
AADHAAR_MASKED = re.compile(r"\bX{4}\s?X{4}\s?\d{4}\b", re.IGNORECASE)  # XXXX XXXX 1234
DOB_PATTERNS = [
    re.compile(r"\b\d{2}[-/]\d{2}[-/]\d{4}\b"),  # 01/01/1998
    re.compile(r"\b\d{2}[-/]\d{2}[-/]\d{2}\b"),  # 01/01/98
]

# Lightweight keyword signals (English only in MVP)
AADHAAR_KEYWORDS = [
    "uidai",
    "unique identification",
    "government of india",
    "republic of india",
    "aadhaar",
]
PAN_KEYWORDS = [
    "income tax department",
    "permanent account number",
    "govt of india",
    "government of india",
    "pan",
]


def _norm(text: str) -> str:
    return (text or "").lower()


def _any_regex_hit(patterns: List[re.Pattern], text: str) -> bool:
    return any(p.search(text) is not None for p in patterns)


def _dob_format_ok(dob_value: Optional[str]) -> bool:
    if not dob_value:
        return False
    s = str(dob_value).strip()
    return any(p.search(s) is not None for p in DOB_PATTERNS)


def _pan_format_ok(pan_value: Optional[str]) -> bool:
    if not pan_value:
        return False
    return PAN_REGEX.search(str(pan_value).strip().upper()) is not None


def _aadhaar_format_ok(aadhaar_value: Optional[str]) -> bool:
    if not aadhaar_value:
        return False
    s = str(aadhaar_value).strip()
    # accept masked or full or OCR spacing variants
    if AADHAAR_MASKED.search(s) or AADHAAR_12_DIGIT.search(s):
        return True
    # if LLM returned just digits without spaces
    digits = re.sub(r"\D", "", s)
    return len(digits) == 12


def _keyword_hits(keywords: List[str], text_norm: str) -> List[str]:
    hits = []
    for k in keywords:
        if k in text_norm:
            hits.append(k)
    return hits


# ----------------------------
# Classification
# ----------------------------

def classify_document(ocr_text: str, qr_present: bool) -> Dict[str, Any]:
    """
    Returns:
      document_type: AADHAAR_LIKELY | PAN_LIKELY | UNKNOWN
      confidence_score: 0-100
      signals: list[str]
      explanation: short text
    """
    t = _norm(ocr_text)

    aadhaar_kw = _keyword_hits(AADHAAR_KEYWORDS, t)
    pan_kw = _keyword_hits(PAN_KEYWORDS, t)

    pan_hit = PAN_REGEX.search(ocr_text.upper() if ocr_text else "") is not None
    aadhaar_full_hit = AADHAAR_12_DIGIT.search(ocr_text or "") is not None
    aadhaar_masked_hit = AADHAAR_MASKED.search(ocr_text or "") is not None

    signals: List[str] = []

    # Score Aadhaar
    aadhaar_score = 0
    if qr_present:
        aadhaar_score += 25
        signals.append("QR_PRESENT")
    if aadhaar_full_hit or aadhaar_masked_hit:
        aadhaar_score += 45
        signals.append("AADHAAR_NUMBER_PATTERN")
    aadhaar_score += min(30, 10 * len(aadhaar_kw))
    if aadhaar_kw:
        signals.append("AADHAAR_KEYWORDS")

    # Score PAN
    pan_score = 0
    if pan_hit:
        pan_score += 70
        signals.append("PAN_ALPHANUM_PATTERN")
    pan_score += min(30, 10 * len(pan_kw))
    if pan_kw:
        signals.append("PAN_KEYWORDS")

    # Decide
    if aadhaar_score >= 60 and aadhaar_score >= pan_score:
        doc_type = "AADHAAR_LIKELY"
        confidence = min(100, aadhaar_score)
        explanation = "Classified as Aadhaar-like using QR presence, 12-digit/masked pattern, and keywords."
    elif pan_score >= 60 and pan_score > aadhaar_score:
        doc_type = "PAN_LIKELY"
        confidence = min(100, pan_score)
        explanation = "Classified as PAN-like using PAN regex pattern and keywords."
    else:
        doc_type = "UNKNOWN"
        confidence = max(aadhaar_score, pan_score)  # show best effort
        explanation = "Insufficient signals to classify confidently as Aadhaar or PAN."

    return {
        "document_type": doc_type,
        "confidence_score": confidence,
        "signals": sorted(list(set(signals)))[:10],
        "aadhaar_score": aadhaar_score,
        "pan_score": pan_score,
        "explanation": explanation,
    }


# ----------------------------
# Plausibility Validation
# ----------------------------

def validate_plausibility(doc_type: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Plausibility checks only. Not legal authentication.
    Returns verdict, score, reason_codes, missing_fields, checks.
    """
    reason_codes: List[str] = []
    checks: Dict[str, Any] = {}
    score = 0

    # Shared fields from your MVP extraction
    name = extracted.get("name")
    dob = extracted.get("date_of_birth")
    address = extracted.get("address")

    if name:
        score += 15
        checks["name_present"] = True
    else:
        reason_codes.append("MISSING_NAME")
        checks["name_present"] = False

    dob_ok = _dob_format_ok(dob)
    checks["dob_format_ok"] = dob_ok
    if dob_ok:
        score += 15
    else:
        reason_codes.append("DOB_FORMAT_SUSPECT")

    if address:
        score += 10
        checks["address_present"] = True
    else:
        checks["address_present"] = False
        reason_codes.append("MISSING_ADDRESS")

    # Type-specific checks
    if doc_type == "PAN_LIKELY":
        pan = extracted.get("pan_number") or extracted.get("id_number")  # fallback to id_number
        pan_ok = _pan_format_ok(pan)
        checks["pan_format_ok"] = pan_ok
        if pan_ok:
            score += 40
        else:
            reason_codes.append("PAN_FORMAT_SUSPECT")

        # Optional: father_name (common in PAN), if you later extract it
        if extracted.get("father_name"):
            score += 5
            checks["father_name_present"] = True
        else:
            checks["father_name_present"] = False

    elif doc_type == "AADHAAR_LIKELY":
        aadhaar = extracted.get("aadhaar_number") or extracted.get("id_number")
        aadhaar_ok = _aadhaar_format_ok(aadhaar)
        checks["aadhaar_format_ok"] = aadhaar_ok
        if aadhaar_ok:
            score += 40
        else:
            reason_codes.append("AADHAAR_FORMAT_SUSPECT")

        # Optional: gender (common in Aadhaar), if you later extract it
        if extracted.get("gender"):
            score += 5
            checks["gender_present"] = True
        else:
            checks["gender_present"] = False

    else:
        # Unknown docs: require stronger baseline field presence
        if name and dob_ok:
            score += 15
        reason_codes.append("DOC_TYPE_UNKNOWN")

    # Verdict thresholds
    if score >= 75:
        verdict = "PASS_PLAUSIBILITY"
    elif score >= 45:
        verdict = "NEEDS_REVIEW"
    else:
        verdict = "FAIL_PLAUSIBILITY"

    missing_fields = [k for k in ["name", "date_of_birth"] if not extracted.get(k)]

    return {
        "verdict": verdict,
        "score": min(100, score),
        "reason_codes": reason_codes[:10],
        "missing_required_fields": missing_fields,
        "checks": checks,
        "disclaimer": "Plausibility checks only. Legal authenticity requires issuer/registry verification.",
    }
