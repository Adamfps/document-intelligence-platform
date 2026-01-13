"""
Document Intelligence Platform (Demo) - Streamlit Application

Platform-style demo that implements core layers:
1) Ingestion (image upload + metadata)
2) Document Intelligence (OCR + LLM extraction)
3) Classification (Aadhaar vs PAN vs Unknown)
4) Validation (plausibility checks + explainable scoring)
5) Auditability (SQLite logs + status lifecycle)

NOTE:
- This demo does not prove legal authenticity.
- Authenticity requires issuer/registry integration (UIDAI/ITD, etc.).
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import streamlit as st

from database import init_db, insert_document, update_document_status, save_extraction
from llm_extractor import extract_fields
from qr_detector import detect_qr_presence
from verification_engine import classify_document, validate_plausibility

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("doc_platform_demo")

# ---------- Constants ----------
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

# ---------- Page config ----------
st.set_page_config(page_title="Document Intelligence Platform (Demo)", page_icon="📄", layout="wide")

# ---------- DB init ----------
try:
    init_db()
except Exception as e:
    logger.exception("Database init failed: %s", e)
    st.error("Failed to initialize database. Check terminal logs.")
    st.stop()

# ---------- Session state ----------
defaults = {
    "stage": "upload",  # upload | results
    "document_id": None,
    "image_path": None,
    "ocr_text": None,
    "extracted_data": None,
    "error": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def reset_state() -> None:
    st.session_state.stage = "upload"
    st.session_state.document_id = None
    st.session_state.image_path = None
    st.session_state.ocr_text = None
    st.session_state.extracted_data = None
    st.session_state.error = None
    st.rerun()


def save_upload(uploaded_file) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    safe_name = uploaded_file.name.replace("/", "_").replace("\\", "_")
    out_path = UPLOADS_DIR / f"{ts}_{safe_name}"
    out_path.write_bytes(uploaded_file.getbuffer())
    return out_path


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _status_safe_update(doc_id: int, status: str) -> None:
    try:
        update_document_status(doc_id, status)
    except Exception:
        # If DB enforces allowed statuses and you didn't update them, don't crash the app
        logger.warning("Status update failed (status=%s). Continuing.", status)


def process_document(uploaded_file) -> None:
    """
    Pipeline:
    - Save upload
    - Insert DB record
    - OCR text extraction
    - QR presence detection (presence only, no decoding)
    - LLM extraction (structured fields)
    - Doc classification (Aadhaar vs PAN vs Unknown)
    - Plausibility validation (explainable)
    - Save extraction payload to DB
    """
    try:
        image_path = save_upload(uploaded_file)
        st.session_state.image_path = str(image_path)

        doc_id = insert_document(image_path.name, status="UPLOADED")
        st.session_state.document_id = doc_id

        # ---------- OCR ----------
        _status_safe_update(doc_id, "OCR_RUNNING")

        # Lazy import OCR so Streamlit UI loads before EasyOCR initializes
        from ocr_processor import extract_text

        with st.spinner("Running OCR..."):
            ocr_text = extract_text(str(image_path))

        if ocr_text is None or len(ocr_text.strip()) == 0:
            _status_safe_update(doc_id, "OCR_FAILED")
            st.session_state.error = "OCR failed or returned empty text. Try a clearer image."
            st.session_state.ocr_text = ""
            st.session_state.extracted_data = None
            st.session_state.stage = "results"
            return

        st.session_state.ocr_text = ocr_text
        _status_safe_update(doc_id, "OCR_DONE")

        # ---------- QR presence detection (platform-ready, no decoding) ----------
        _status_safe_update(doc_id, "QR_SCAN_RUNNING")
        with st.spinner("Checking QR presence..."):
            qr_info = detect_qr_presence(str(image_path))
        _status_safe_update(doc_id, "QR_SCAN_DONE")

        qr_present = bool(qr_info.get("qr_present", False))

        # ---------- LLM extraction ----------
        _status_safe_update(doc_id, "LLM_RUNNING")
        with st.spinner("Calling LLM to extract fields..."):
            extracted = extract_fields(ocr_text)
        _status_safe_update(doc_id, "LLM_DONE")

        if not isinstance(extracted, dict):
            extracted = {}

        # ---------- Classification + Validation ----------
        _status_safe_update(doc_id, "VERIFY_RUNNING")
        with st.spinner("Classifying and validating..."):
            doc_classification = classify_document(ocr_text, qr_present=qr_present)
            verification = validate_plausibility(doc_classification.get("document_type", "UNKNOWN"), extracted)
        _status_safe_update(doc_id, "VERIFY_DONE")

        # Attach platform outputs into final payload for auditability
        extracted["platform"] = {
            "doc_classification": doc_classification,
            "verification": verification,
            "qr_presence": qr_info,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        }

        st.session_state.extracted_data = extracted
        save_extraction(doc_id, extracted)

        _status_safe_update(doc_id, "COMPLETED")

        st.session_state.error = None
        st.session_state.stage = "results"

    except Exception as e:
        logger.exception("Processing error: %s", e)
        if st.session_state.document_id:
            try:
                update_document_status(st.session_state.document_id, "ERROR")
            except Exception:
                pass
        st.session_state.error = f"Error: {e}"
        st.session_state.stage = "results"


# ---------- UI ----------
st.title("📄 Document Intelligence Platform (Demo)")
st.caption("Upload an image → OCR → LLM extraction → classification → plausibility validation → stored in SQLite")

st.info(
    "This demo performs document intelligence and plausibility checks. It does not prove legal authenticity without issuer/registry integration.",
    icon="⚠️",
)

if st.session_state.stage == "upload":
    uploaded = st.file_uploader(
        "Upload an ID image (JPG/PNG)",
        type=["jpg", "jpeg", "png"],
        help="Use sample / masked IDs only. Do not upload real personal documents.",
    )

    if uploaded is not None:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(uploaded, caption="Preview", use_container_width=True)

        with col2:
            if st.button("Process Document", type="primary"):
                process_document(uploaded)
                st.rerun()

    with st.expander("ℹ️ What this platform demo does"):
        st.markdown(
            """
**Implemented platform layers (demo):**
- Ingestion: image upload + metadata
- Intelligence: OCR + structured extraction via LLM
- Classification: Aadhaar-like vs PAN-like vs Unknown (explainable signals)
- Validation: rule-based plausibility scoring + reason codes
- Auditability: status lifecycle + DB persistence

**Not implemented in demo (by design):**
- Legal authentication via UIDAI/ITD registries
- Cryptographic QR decoding / signature verification
- Fraud detection (tamper, duplicates)
- Multi-language OCR and PDFs
            """
        )

elif st.session_state.stage == "results":
    left, right = st.columns([1, 1])

    with left:
        st.subheader("Uploaded Image")
        if st.session_state.image_path:
            st.image(st.session_state.image_path, use_container_width=True)

        st.subheader("Raw OCR Text")
        with st.expander("View OCR output"):
            st.text(st.session_state.ocr_text or "(no OCR text)")

    with right:
        st.subheader("Classification + Validation")

        if st.session_state.error:
            st.error(st.session_state.error)
        else:
            st.success("Processing complete")

        extracted: Dict[str, Any] = st.session_state.extracted_data or {}
        platform = extracted.get("platform", {})

        # ---- QR presence ----
        qr = platform.get("qr_presence", {})
        if qr:
            st.write(f"**QR Present:** {bool(qr.get('qr_present', False))}")
            note = qr.get("note")
            if note:
                st.caption(note)

        # ---- Classification ----
        dc = platform.get("doc_classification", {})
        if dc:
            doc_type = dc.get("document_type", "UNKNOWN")
            conf = dc.get("confidence_score", 0)

            if doc_type == "AADHAAR_LIKELY":
                st.success(f"**Document Type:** {doc_type}  |  **Confidence:** {conf}/100")
            elif doc_type == "PAN_LIKELY":
                st.success(f"**Document Type:** {doc_type}  |  **Confidence:** {conf}/100")
            else:
                st.warning(f"**Document Type:** {doc_type}  |  **Confidence:** {conf}/100")

            signals = dc.get("signals", [])
            if signals:
                st.caption("Signals: " + ", ".join(signals))

            expl = dc.get("explanation", "")
            if expl:
                st.caption(expl)

        # ---- Validation ----
        vf = platform.get("verification", {})
        if vf:
            st.divider()
            verdict = vf.get("verdict", "UNKNOWN")
            score = vf.get("score", 0)

            if verdict == "PASS_PLAUSIBILITY":
                st.success(f"**Verdict:** {verdict}  |  **Score:** {score}/100")
            elif verdict == "NEEDS_REVIEW":
                st.warning(f"**Verdict:** {verdict}  |  **Score:** {score}/100")
            else:
                st.error(f"**Verdict:** {verdict}  |  **Score:** {score}/100")

            missing = vf.get("missing_required_fields", [])
            if missing:
                st.warning("Missing required fields: " + ", ".join(missing))

            reasons = vf.get("reason_codes", [])
            if reasons:
                st.caption("Reasons: " + ", ".join(reasons))

            checks = vf.get("checks", {})
            if checks:
                passed = sum(1 for v in checks.values() if v)
                total = len(checks)
                st.caption(f"Checks passed: {passed}/{total}")

            disc = vf.get("disclaimer", "")
            if disc:
                st.caption(f"⚠️ {disc}")

        # ---- Extracted fields (exclude platform metadata) ----
        st.divider()
        st.subheader("Extracted Fields")

        table_rows = []
        for k, v in extracted.items():
            if k == "platform":
                continue
            if v is None or v == "":
                display_value = "Not found"
            elif isinstance(v, (dict, list)):
                display_value = _safe_json(v)
            else:
                display_value = str(v)
            table_rows.append({"Field": k.replace("_", " ").title(), "Value": display_value})

        if table_rows:
            st.table(table_rows)
        else:
            st.info("No extracted fields available.")

        st.download_button(
            label="Download JSON",
            data=json.dumps(extracted, ensure_ascii=False, indent=2),
            file_name="extracted_data.json",
            mime="application/json",
        )

    st.divider()
    if st.button("Upload Another", type="secondary"):
        reset_state()
