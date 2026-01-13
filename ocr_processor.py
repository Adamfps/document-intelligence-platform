"""
OCR processing module for Document Intelligence Platform (Demo).

Text extraction from images using EasyOCR (English-only, CPU).
Adds:
- confidence filtering to reduce garbage OCR
- line breaks to preserve layout cues
"""

import logging
from typing import Optional, List, Tuple

import easyocr

logger = logging.getLogger(__name__)

_reader = None


def _get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        logger.info("Initializing EasyOCR reader (English, CPU mode)...")
        _reader = easyocr.Reader(["en"], gpu=False)
        logger.info("EasyOCR reader initialized successfully")
    return _reader


def extract_text(image_path: str, min_conf: float = 0.35) -> Optional[str]:
    """
    Extract text from an image using EasyOCR.

    Args:
        image_path: Path to the image file
        min_conf: minimum confidence threshold for keeping a text chunk

    Returns:
        Extracted text as a single string with line breaks, or None if failed.
    """
    try:
        reader = _get_reader()

        # results: List[Tuple[bbox, text, conf]]
        results = reader.readtext(image_path)

        if not results:
            return ""

        kept: List[str] = []
        dropped = 0

        for r in results:
            if len(r) < 3:
                continue
            text = str(r[1]).strip()
            conf = float(r[2]) if r[2] is not None else 0.0

            if not text:
                continue

            if conf >= min_conf:
                kept.append(text)
            else:
                dropped += 1

        # Preserve some layout via line breaks
        extracted_text = "\n".join(kept).strip()

        logger.info("OCR done for %s | kept=%s dropped=%s", image_path, len(kept), dropped)
        return extracted_text

    except Exception as e:
        logger.exception("OCR extraction error: %s", e)
        return None
