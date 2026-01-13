"""
LLM extraction module for Document Intelligence Platform (Demo).

Structured field extraction from OCR text using Groq API.
"""

import os
import json
import logging
from typing import Dict, Any, Optional


from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MODEL_NAME = "llama-3.3-70b-versatile"

REQUIRED_FIELDS = [
    "name",
    "date_of_birth",
    "address",
    "id_number",
    "aadhaar_number",
    "pan_number",
    "gender",
    "father_name",
]

# Create client lazily (so import doesn't crash if key missing)
_client: Optional[Groq] = None


def _get_client() -> Optional[Groq]:
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    _client = Groq(api_key=api_key)
    return _client


def extract_fields(ocr_text: str) -> Dict[str, Any]:
    """
    Extract structured fields from OCR text using Groq LLM.

    Returns a dict with REQUIRED_FIELDS keys.
    Missing fields are None.
    """
    client = _get_client()
    if client is None:
        logger.error("GROQ_API_KEY not found. Returning null fields.")
        return {field: None for field in REQUIRED_FIELDS}

    if not ocr_text or not ocr_text.strip():
        logger.warning("Empty OCR text provided. Returning null fields.")
        return {field: None for field in REQUIRED_FIELDS}

    prompt = f"""Extract fields from this Indian identity document text. Return ONLY valid JSON.

Fields:
name, date_of_birth, address,
id_number,
aadhaar_number, pan_number,
gender, father_name

Rules:
- If a field is not present, use null.
- Aadhaar number may be masked like XXXX XXXX 1234; return it as seen.
- PAN format is ABCDE1234F.

Text:
{ocr_text}

JSON:"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a document extraction assistant. Return valid JSON only, no extra text.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        response_text = (response.choices[0].message.content or "").strip()
        if not response_text:
            logger.warning("Empty LLM response. Returning null fields.")
            return {field: None for field in REQUIRED_FIELDS}

        extracted_data = json.loads(response_text)

        # Normalize to required keys only
        result: Dict[str, Any] = {}
        for field in REQUIRED_FIELDS:
            v = extracted_data.get(field, None)
            if v is None:
                result[field] = None
            else:
                result[field] = str(v).strip() if str(v).strip() else None

        return result

    except json.JSONDecodeError as e:
        logger.error("LLM JSON parsing error: %s", e)
        return {field: None for field in REQUIRED_FIELDS}
    except Exception as e:
        logger.error("LLM extraction error: %s", e)
        return {field: None for field in REQUIRED_FIELDS}
