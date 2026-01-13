from typing import Dict, Any
import cv2


def detect_qr_presence(image_path: str) -> Dict[str, Any]:
    """
    Detect whether a QR code is visually present in the image.

    IMPORTANT:
    - Detection only
    - No decoding
    - No cryptographic verification
    - No issuer validation
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {
                "qr_present": False,
                "confidence": 0.0,
                "method": "opencv",
                "authoritative": False,
                "error": "image_read_failed",
            }

        detector = cv2.QRCodeDetector()
        _, points, _ = detector.detectAndDecode(img)

        qr_present = points is not None and len(points) > 0

        return {
            "qr_present": bool(qr_present),
            "confidence": 0.9 if qr_present else 0.0,  # heuristic
            "method": "opencv",
            "authoritative": False,
            "note": "Visual QR presence only. No decoding or validation performed.",
        }

    except Exception as e:
        return {
            "qr_present": False,
            "confidence": 0.0,
            "method": "opencv",
            "authoritative": False,
            "error": str(e),
        }
