from typing import Dict, Any
from verification_engine import validate_plausibility


def route_validation(doc_classification: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Routes validation based on classified document type.
    Today: plausibility rules only.
    Future: can plug in issuer registry checks here.
    """
    doc_type = doc_classification.get("document_type", "UNKNOWN")
    return validate_plausibility(doc_type, extracted)
