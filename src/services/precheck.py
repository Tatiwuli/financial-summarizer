from src.utils.pdf_processor import PDFProcessingError, create_pdf_processor
from src.config.runtime import CALL_TYPE, SUMMARY_LENGTH, PDF_PATH, TRANSCRIPTS_DIR


class PrecheckError(Exception):
    def __init__(self, code: str, message: str):
        # essa mensagem vem do `e` do proprio  exception Exception as e
        super().__init__(message)
        self.code = code
        # esses sao atributos que voce escreve para renderizar no frontend.
        self.message = message


def run_precheck():
    processor = create_pdf_processor(transcripts_dir=TRANSCRIPTS_DIR)
    try:
        result = processor.process_pdf(PDF_PATH)

    except PDFProcessingError as e:
        raise PrecheckError("pdf_processing_error", str(e))

    pres_len = result.get("presentation_text_length")
    qa_len = result.get("qa_text_length")

    envelope = {
        "title": result.get("original_filename") or "Documento",
        "call_type": CALL_TYPE,
        "blocks": [
            {
                "type": "precheck",
                "data": {
                    "summary_length": SUMMARY_LENGTH,
                    "qa_transcript": result.get("qa_transcript"),
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
