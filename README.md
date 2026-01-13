# AI-Powered Document Intelligence Platform

A document intelligence platform that extracts, classifies, and performs explainable plausibility checks on Indian identity documents using OCR and Large Language Models.

This project focuses on **document understanding**, not just text extraction.  
It demonstrates how manual document verification workflows can be augmented with AI in a safe, auditable, and explainable way.

> ⚠️ This system performs **plausibility checks only** and is **not a legal authentication system**.

---

## ✨ What This Platform Does

- Accepts ID images (JPG / PNG)
- Extracts raw text using OCR
- Converts unstructured text into structured fields using an LLM
- Detects QR **presence** (no decoding)
- Classifies document type:
  - Aadhaar-like
  - PAN-like
  - Unknown
- Runs explainable plausibility checks with reason codes
- Stores results in SQLite for auditability
- Exports structured output as JSON

---

## 🧠 Why This Is Different From OCR Demos

Most OCR tools stop at text extraction.

This platform goes further by:
- Understanding **what document** is being submitted
- Explaining **why** a document looks valid or suspicious
- Returning structured, auditable outputs instead of raw text
- Respecting real-world constraints (e.g. no unauthorized QR decoding)

---

## 🏗 High-Level Architecture

User Upload
|
v
Streamlit UI (app.py)
|
v
OCR (EasyOCR)
|
v
QR Presence Detection (visual only)
|
v
LLM-Based Field Extraction
|
v
Document Classification + Plausibility Checks
|
v
SQLite Storage + JSON Output


---

## 🧪 How It Works (End-to-End Flow)

1. User uploads an ID image
2. OCR extracts raw text from the image
3. QR presence is detected (not decoded)
4. LLM extracts structured fields (name, DOB, ID numbers, etc.)
5. Verification engine:
   - Classifies document type
   - Runs plausibility checks
6. Results are displayed and stored
7. Output can be downloaded as JSON

---

## 📂 Extracted Fields

- `name`
- `date_of_birth`
- `address`
- `id_number`
- `aadhaar_number`
- `pan_number`
- `gender`
- `father_name`

Fields not found are returned as `null`.

---

## ⚖️ Why QR Codes Are Not Decoded

This platform **intentionally does not decode Aadhaar QR codes**.

Reason:
- Aadhaar QR verification requires UIDAI-issued cryptographic public keys
- Decoding QR payloads without official authorization would be insecure and misleading

Instead, the system:
- Detects QR **presence**
- Treats QR verification as an **external authority responsibility**

This reflects real-world, governance-grade system boundaries.

---

## 🚀 Local Setup

### Prerequisites
- Python 3.8+
- Groq API key

### Installation

```bash
pip install -r requirements.txt

Create a .env file:

GROQ_API_KEY=your_groq_api_key_here


Run the app:

streamlit run app.py
