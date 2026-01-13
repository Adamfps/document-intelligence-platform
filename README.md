# Document Verify MVP

Document Verify MVP is a lightweight, end-to-end demo that extracts structured data from ID images using OCR + LLM, then classifies and scores plausibility with explainable signals. It is designed for capstone/demo use, not legal authentication.

## Features

- Image upload (JPG/PNG)
- OCR text extraction (EasyOCR, English)
- Structured field extraction (Groq LLM)
- QR presence detection (visual only, no decoding)
- Classification (Aadhaar-like vs PAN-like vs Unknown)
- Plausibility scoring with reason codes
- SQLite persistence and audit trail
- JSON download of extracted payload

## Architecture (High-Level)

```
User Upload
    |
    v
Streamlit UI (app.py)
    |
    v
OCR (ocr_processor.py) ---> Raw Text
    |
    v
QR Presence (qr_detector.py)
    |
    v
LLM Extract (llm_extractor.py) ---> Structured Fields
    |
    v
Classify + Validate (verification_engine.py)
    |
    v
SQLite (database.py) ---> Audit Logs + Payload
```

## Local Setup

### Prerequisites

- Python 3.8+
- Groq API key

### Install

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` in `doc-verify-mvp/`:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

Run the app:

```bash
streamlit run app.py
```

## Usage

1. Upload a sample ID image (JPG/PNG).
2. Click "Process Document".
3. View OCR text, classification, plausibility verdict, and extracted fields.
4. Download results as JSON.

## Extracted Fields

- `name`
- `date_of_birth`
- `address`
- `id_number`
- `aadhaar_number`
- `pan_number`
- `gender`
- `father_name`

## Limitations

- Plausibility checks only; not legal authentication.
- No QR decoding or cryptographic verification.
- Heuristic classification based on keywords/regex.
- English-only OCR; no PDFs or multi-language support.
- Accuracy depends on image quality.

## Project Structure

```
doc-verify-mvp/
├── app.py                 # Streamlit UI + pipeline controller
├── database.py            # SQLite schema & CRUD
├── ocr_processor.py       # OCR logic
├── llm_extractor.py       # Groq LLM extraction
├── verification_engine.py # Classification + plausibility rules
├── qr_detector.py         # QR presence detection
├── requirements.txt       # Python dependencies
├── .env                   # API keys (not committed)
├── .gitignore
├── uploads/               # saved images
└── verification.db        # SQLite database
```

## Demo Data

Generate sample Aadhaar-like and PAN-like images:

```bash
python generate_test_ids.py
```
