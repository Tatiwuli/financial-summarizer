import os
from datetime import datetime
from fastapi import UploadFile
from src.utils.pdf_processor import PDFProcessingError, create_pdf_processor
from src.config.constants import CACHE_DIR
import json
import hashlib


class PrecheckError(Exception):
    def __init__(self, code: str, message: str):
        # Getting the message from the built-in Exception
        super().__init__(message)
        self.code = code
        self.message = message 


def run_validate_file(file: UploadFile, call_type: str, summary_length: str, answer_format: str = "prose"):
    processor = create_pdf_processor(save_transcripts_dir=CACHE_DIR)

    original_filename = (file.filename or "transcript.pdf")

    # Read bytes directly
    pdf_bytes = file.file.read()
    try:
        # Preserve user-provided filename
        result = processor.process_pdf_bytes(
            pdf_bytes, original_filename=original_filename
        )

        # DEBUG: Log the extracted content lengths and snippets
        pres_transcript = result.get("presentation_transcript", "")

        qa_transcript = result.get("q_a_transcript", "")

        if pres_transcript:
            print(
                f"[PRECHECK] Presentation preview (first 200 chars): {pres_transcript[:200]}...")

        if qa_transcript:
            print(
                f"[PRECHECK] Q&A preview (first 200 chars): {qa_transcript[:200]}...")
        else:
            print("[PRECHECK] Q&A transcript is empty or None!")

    except PDFProcessingError as e:

        raise PrecheckError("pdf_processing_error", str(e))

    # Build payload to persist server-side
    save_transcript_data = {

        "validated_at": datetime.now().isoformat(),
        "input": {
            "call_type": call_type,
            "summary_length": summary_length,
            "answer_format": answer_format,
            "filename": os.path.basename(original_filename),
        },
        "transcripts": {
            "presentation": result.get("presentation_transcript") or "",
            "q_a": result.get("q_a_transcript") or "",
        },
    }

    # Compute content hash (normalized simple hash)
    norm_p = (save_transcript_data["transcripts"]
              ["presentation"] or "").strip()
    norm_q = (save_transcript_data["transcripts"]["q_a"] or "").strip()
    combined = (norm_p + "\n\n" + norm_q).encode("utf-8", errors="ignore")
    content_hash = hashlib.sha256(combined).hexdigest()

    save_transcript_data["content_hash"] = content_hash

    # Use the literal original filename for the transcript JSON name
    base_name = os.path.basename(original_filename or "transcript.pdf")
    json_name = os.path.splitext(base_name)[0] + ".json"
    json_path = os.path.join(CACHE_DIR, json_name)

    save_transcript_data["transcript_name"] = json_name

    # If a JSON with the same literal name exists, compare content hashes
    # - If equal: reuse existing JSON (skip saving)
    # - If different or unreadable: overwrite by saving the new JSON
    reuse_existing = False
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if existing.get("content_hash") == content_hash:
                reuse_existing = True
                print(f"[PRECHECK] Reusing existing transcript: {json_path}")
        except Exception:
            # If failed to read the existing file, ignore the error and overwrite it with the new one
            reuse_existing = False

    if not reuse_existing:  # save it
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(save_transcript_data, f, ensure_ascii=False)

    # Output for frontend
    output = {
        "is_validated": True,
        "validated_at": datetime.now().isoformat(),
        "input": {
            "call_type": call_type,
            "summary_length": summary_length,
            "answer_format": answer_format,
            # it will be the same with the matched existing file
            "filename": os.path.basename(original_filename),
        },
        "transcript_name": json_name,
    }

    return output
