import os
from datetime import datetime
from fastapi import UploadFile
from src.utils.pdf_processor import PDFProcessingError, create_pdf_processor
from src.config.runtime import TRANSCRIPTS_DIR
import json
import hashlib


class PrecheckError(Exception):
    def __init__(self, code: str, message: str):
        # essa mensagem vem do `e` do proprio  exception Exception as e
        super().__init__(message)
        self.code = code
        # esses sao atributos que voce escreve para renderizar no frontend.
        self.message = message


def run_validate_file(file: UploadFile, call_type: str, summary_length: str):
    processor = create_pdf_processor(save_transcripts_dir=TRANSCRIPTS_DIR)

    # Read bytes directly (no temp file)
    pdf_bytes = file.file.read()
    try:
        # Preserve user-provided filename for deduplication
        result = processor.process_pdf_bytes(
            pdf_bytes, original_filename=(file.filename or None)
        )

        # DEBUG: Log all keys in the result
        print(f"[DEBUG PRECHECK] Result keys: {list(result.keys())}")
        print(f"[DEBUG PRECHECK] Full result: {result}")

        # DEBUG: Log the extracted content lengths and snippets
        pres_transcript = result.get("presentation_transcript", "")
        # Fixed: use correct key with underscore
        qa_transcript = result.get("q_a_transcript", "")

        print(f"[DEBUG PRECHECK] Presentation length: {len(pres_transcript)}")
        print(f"[DEBUG PRECHECK] Q&A length: {len(qa_transcript)}")
        print(f"[DEBUG PRECHECK] Q&A transcript exists: {bool(qa_transcript)}")

        if pres_transcript:
            print(
                f"[DEBUG PRECHECK] Presentation preview (first 200 chars): {pres_transcript[:200]}...")

        if qa_transcript:
            print(
                f"[DEBUG PRECHECK] Q&A preview (first 200 chars): {qa_transcript[:200]}...")
        else:
            print("[DEBUG PRECHECK] Q&A transcript is empty or None!")

    except PDFProcessingError as e:
        print(f"[DEBUG PRECHECK] PDF Processing error: {e}")
        raise PrecheckError("pdf_processing_error", str(e))

    finally:
        pass

    pres_len = result.get("presentation_text_length")
    qa_len = result.get("qa_text_length")

    # Build payload to persist server-side
    save_transcript_data = {

        "validated_at": datetime.now().isoformat(),
        "input": {
            "call_type": call_type,
            "summary_length": summary_length,
            "filename": result.get("original_filename"),
        },
        "transcripts": {
            "presentation": result.get("presentation_transcript") or "",
            "q_a": result.get("q_a_transcript") or "",
        },
    }

    # Compute content hash for dedup (normalized simple hash)
    norm_p = (save_transcript_data["transcripts"]
              ["presentation"] or "").strip()
    norm_q = (save_transcript_data["transcripts"]["q_a"] or "").strip()
    combined = (norm_p + "\n\n" + norm_q).encode("utf-8", errors="ignore")
    content_hash = hashlib.sha256(combined).hexdigest()

    # Disambiguate on collision with different content
    safe_base = os.path.basename(result.get(
        "original_filename") or "transcript.pdf")
    safe_base = "".join(
        c if c.isalnum() or c in ".-_" else "_" for c in safe_base)
    json_name = os.path.splitext(safe_base)[0] + ".json"
    json_path = os.path.join(TRANSCRIPTS_DIR, json_name)

    # If file exists, check if same content_hash; if different, suffix
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if existing.get("content_hash") != content_hash:
                base_no_ext = os.path.splitext(json_name)[0]
                json_name = base_no_ext + " (2).json"
                json_path = os.path.join(TRANSCRIPTS_DIR, json_name)
        except Exception:
            # If unreadable, fall back to suffix to avoid overwrite
            base_no_ext = os.path.splitext(json_name)[0]
            json_name = base_no_ext + " (2).json"
            json_path = os.path.join(TRANSCRIPTS_DIR, json_name)

    save_transcript_data["content_hash"] = content_hash
    save_transcript_data["transcript_name"] = json_name

    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(save_transcript_data, f, ensure_ascii=False)

    # Output for frontend
    output = {
        "is_validated": True,
        "validated_at": datetime.now().isoformat(),
        "input": {
            "call_type": call_type,
            "summary_length": summary_length,
            "filename": result.get("original_filename"),
        },
        "transcript_name": json_name,
    }

    return output
