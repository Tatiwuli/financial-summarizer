import os
import tempfile
from fastapi import UploadFile
from src.utils.pdf_processor import PDFProcessingError, create_pdf_processor
from src.config.runtime import CALL_TYPE, TRANSCRIPTS_DIR


class PrecheckError(Exception):
    def __init__(self, code: str, message: str):
        # essa mensagem vem do `e` do proprio  exception Exception as e
        super().__init__(message)
        self.code = code
        # esses sao atributos que voce escreve para renderizar no frontend.
        self.message = message


def run_precheck(file: UploadFile):
    processor = create_pdf_processor(transcripts_dir=TRANSCRIPTS_DIR)

    # Create  a temporary file to get the uploaded file content
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file.file.read())
        temp_file_path = temp_file.name

    try:
        result = processor.process_pdf(temp_file_path)

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
        os.unlink(temp_file_path)  # delete the temporary file

    pres_len = result.get("presentation_text_length")
    qa_len = result.get("qa_text_length")

    envelope = {
        "title": result.get("original_filename") or "Documento",
        "call_type": CALL_TYPE,
        "blocks": [
            {
                "type": "precheck",
                "data": {
                    # Fixed: use correct key
                    "qa_transcript": result.get("q_a_transcript"),
                    "presentation_transcript": result.get("presentation_transcript"),
                    "pdf": {
                        "original_filename": result.get("original_filename"),
                        "uuid_filename": result.get("uuid_filename"),
                        "transcript_path": result.get("transcript_path"),
                        "presentation_text_length": pres_len,
                        "qa_text_length": qa_len
                    }
                }
            }
        ],
        "meta": {
            "generated_at": None
        }
    }

    return envelope
