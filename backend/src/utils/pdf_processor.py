"""
PDF Processor module for Earnings Call Analyzer
Handles PDF validation, text extraction, and Q&A section identification
"""


import re
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from statistics import mode, StatisticsError
import fitz  # PyMuPDF
from config.file_constants import QA_PATTERNS, FILESIZE,TRANSCRIPT_DIR


class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors"""
    pass


class PDFProcessor:
    """Handles PDF processing operations for earnings call transcripts"""

    def __init__(self, max_file_size_mb: int = FILESIZE, save_transcripts_dir: str = TRANSCRIPT_DIR):

        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.save_transcripts_dir = Path(save_transcripts_dir)
        self.save_transcripts_dir.mkdir(exist_ok=True)
        self.qa_patterns = QA_PATTERNS

# ------------------ FUNCTIONS UTILITIES ------------------------------------------------

    def normalize_file_path(self, file_path: str) -> Path:

        try:
            # Convert to Path object and resolve to absolute path
            path = Path(file_path).resolve()

            # Check if file exists
            if not path.exists():
                raise PDFProcessingError(f"File not found: {file_path}")

            # Check if it's a file (not a directory)
            if not path.is_file():
                raise PDFProcessingError(f"Path is not a file: {file_path}")

            # Check if it's a PDF file
            if path.suffix.lower() != '.pdf':
                raise PDFProcessingError(f"File is not a PDF: {file_path}")

            return path

        except OSError as e:
            raise PDFProcessingError(
                f"Invalid file path: {file_path} - {str(e)}")

    def create_file_path(self, source_path: Path, original_filename: str) -> Tuple[str, str]:

        try:
            # Ensure we only use the base name, and sanitize it for filesystem safety
            base_name = Path(original_filename).name
            # Replace characters not safe for filenames
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", base_name).strip("_")
            if not safe_name:
                safe_name = "transcript.pdf"
            # Ensure .pdf extension
            if not safe_name.lower().endswith(".pdf"):
                safe_name = f"{safe_name}.pdf"

            transcript_path = self.save_transcripts_dir / safe_name

            # If a file with the same name already exists, reuse it (deduplication)
            if transcript_path.exists():
                return safe_name, str(transcript_path)

            # Otherwise, copy the source file
            shutil.copy2(source_path, transcript_path)
            return safe_name, str(transcript_path)
        except Exception as e:
            raise PDFProcessingError(
                f"Failed to create file path for transcript: {str(e)}")

    def validate_file_size(self, file_path: Path) -> None:

        file_size = file_path.stat().st_size
        if file_size > self.max_file_size_bytes:
            size_mb = file_size / (1024 * 1024)
            max_mb = self.max_file_size_bytes / (1024 * 1024)
            raise PDFProcessingError(
                f"File size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_mb}MB)"
            )

    def analyze_font_styles(self,  doc: fitz.Document) -> float:

        try:
           
            font_sizes = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                font_size = span["size"]
                                if font_size > 0:  # Filter out invalid sizes
                                    font_sizes.append(round(font_size, 1))
            if not font_sizes:
                raise PDFProcessingError(
                    "No valid font sizes found in document")

            # Calculate mode (most common font size)
            try:
                body_font_size = mode(font_sizes)
            except StatisticsError:
                # If no mode exists, use median
                font_sizes.sort()
                body_font_size = font_sizes[len(font_sizes) // 2]

            return body_font_size

        except Exception as e:
            raise PDFProcessingError(
                f"Failed to analyze font styles: {str(e)}")

    def find_qa_section_title(self, doc: fitz.Document, body_font_size: float) -> Optional[int]:

        try:
          
            self.qa_patterns = QA_PATTERNS

            min_title_font_size = body_font_size

            # Search from the last page to the first to avoid table of contents
            for page_num in range(len(doc) - 1, -1, -1):
                page = doc.load_page(page_num)
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            line_text = ""
                            line_font_sizes = []
                            line_fonts: List[str] = []

                            for span in line["spans"]:
                                line_text += span["text"]
                                line_font_sizes.append(span["size"])
                                # Collect font names to infer bold
                                font_name = str(span.get("font", "")).lower()
                                if font_name:
                                    line_fonts.append(font_name)

                            line_text = line_text.strip()

                            # Infer bold / heading-like
                            is_bold = any(
                                ("bold" in f or "heavy" in f) for f in line_fonts
                            )

                            # Check if line matches Q&A patterns (case-insensitive)
                            for pattern in self.qa_patterns:

                                if re.search(re.escape(pattern), line_text):
                                    print(
                                        f"[DEBUG EXTRACT] Found Q&A pattern: {pattern}")
                                    if line_font_sizes:
                                        print(
                                            f"[DEBUG EXTRACT] Line font sizes: {line_font_sizes}")
                                        max_size = max(line_font_sizes)
                                        print(
                                            f"[DEBUG EXTRACT] Max size: {max_size}")
                                        # Accept if strictly larger than body, or equal-size within epsilon but bold/heading-like
                                        print(
                                            f"[DEBUG EXTRACT] Min title font size: {min_title_font_size}")
                                        print(
                                            f"[DEBUG EXTRACT] Is bold: {is_bold}")
                                        if max_size > (min_title_font_size) or (max_size == min_title_font_size and is_bold):  # noqa: E50
                                            print(
                                                f"[DEBUG EXTRACT] Found Q&A section at page {page_num}")
                                            q_a_page_num = page_num
                                            return q_a_page_num

                                        # last chance to find Q&A section
                                        elif max_size == min_title_font_size:
                                            q_a_page_num = page_num
                                            print(
                                                f"[DEBUG EXTRACT] Same font size - Found Q&A section at page {page_num}")

                                            return q_a_page_num

                                       

           
            return None

        except Exception as e:
            raise PDFProcessingError(f"Failed to find Q&A section: {str(e)}")

    def extract_text_sections(self, doc: fitz.Document) -> Tuple[str, str]:

        try:
            body_font_size = self.analyze_font_styles(doc)
            print(f"[DEBUG EXTRACT] Body font size: {body_font_size}")

            qa_start_page = self.find_qa_section_title(
                doc       , body_font_size)
            print(f"[DEBUG EXTRACT] Q&A start page: {qa_start_page}")

           
            presentation_transcript = ""
            q_a_transcript = ""

            # If no Q&A section is found, the whole document is the presentation.
            if qa_start_page is None:
                print(
                    "[DEBUG EXTRACT] No Q&A section found - treating entire document as presentation")
                for page_num in range(len(doc)):
                    presentation_transcript += doc.load_page(
                        page_num).get_text()
            else:
                print(
                    f"[DEBUG EXTRACT] Q&A section found starting at page {qa_start_page}")
                # 1. Extract text from pages before the Q&A section
                for page_num in range(qa_start_page):
                    presentation_transcript += doc.load_page(
                        page_num).get_text()

                # 2. Split the page where the Q&A section starts
                page = doc.load_page(qa_start_page)
                page_text = page.get_text()

                qa_start_index = -1
                lowered_page_text = page_text.lower()
                for pattern in self.qa_patterns:
                    # case-insensitive search- need to check if this is reliable
                    found_index = lowered_page_text.find(pattern.lower())
                    if found_index != -1:
                        if qa_start_index == -1 or found_index < qa_start_index:
                            qa_start_index = found_index

                if qa_start_index != -1:
                    presentation_transcript += page_text[:qa_start_index]
                    q_a_transcript += page_text[qa_start_index:]
                else:
                    # Fallback if pattern not found on page (should not happen)
                    presentation_transcript += page_text

                # 3. Extract text from the rest of the pages for the Q&A section
                for page_num in range(qa_start_page + 1, len(doc)):
                    q_a_transcript += doc.load_page(page_num).get_text()

            # 4. Clean up and remove potential copyright page from the end
            if len(doc) > 1:
                last_page = doc.load_page(len(doc) - 1)
                last_page_text = last_page.get_text().strip()

                if last_page_text:
                    last_page_font_sizes = []
                    blocks = last_page.get_text("dict")["blocks"]
                    for block in blocks:
                        if "lines" in block:
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    last_page_font_sizes.append(
                                        round(span["size"], 1))

                    if last_page_font_sizes and max(last_page_font_sizes) < body_font_size:
                        # Decide which text block to trim the copyright from
                        if q_a_transcript and q_a_transcript.strip().endswith(last_page_text):
                            q_a_transcript = q_a_transcript.strip(
                            )[:-len(last_page_text)].strip()
                        elif presentation_transcript.strip().endswith(last_page_text):
                            presentation_transcript = presentation_transcript.strip()[
                                :-len(last_page_text)].strip()

           
            return presentation_transcript.strip(), q_a_transcript.strip()

        except Exception as e:
            raise PDFProcessingError(
                f"Failed to extract text sections: {str(e)}")

    def validate_content(self, text: str, min_alphabetic_chars: int = 250) -> None:

        if not text or not text.strip():
            raise PDFProcessingError("Extracted content is empty")

        # Count alphabetic characters only
        alphabetic_chars = re.sub(r'[^a-zA-Z]', '', text)
        alphabetic_count = len(alphabetic_chars)

        if alphabetic_count < min_alphabetic_chars:
            raise PDFProcessingError(
                f"Insufficient content in {text}: {alphabetic_count} alphabetic characters "
                f"(minimum required: {min_alphabetic_chars})"
            )

    # ------------------ FUNCTIONS WORKFLOWS ------------------------------------------------

    def process_pdf(self, file_path: str) -> Dict:
        """
        Main function to extract text sections from pdf 
        """

        print("Processing PDF starts...")
        print("Normalizing file path: ", file_path)
        # Normalize and validate file path
        normalized_path = self.normalize_file_path(file_path)
        original_filename = normalized_path.name

        # Validate file size ( 10mb)
        print("Validating file size...")
        self.validate_file_size(normalized_path)

        print("Extracting text sections...")
        #  Extract both text sections
        presentation_transcript, q_a_transcript = self.extract_text_sections(
            normalized_path)

        print("Validating content...")
        #  Validate content
        self.validate_content(presentation_transcript)
        if q_a_transcript:  # Only validate Q&A if it exists
            self.validate_content(q_a_transcript)

        print("Saving transcript copy...")
        saved_filename, transcript_path = self.create_file_path(
            normalized_path, original_filename
        )

        # DEBUG: Log extracted content details
        print(
            f"[DEBUG PDF_PROCESSOR] Processing complete for: {original_filename}")
        print(
            f"[DEBUG PDF_PROCESSOR] Presentation length: {len(presentation_transcript)}")
        print(f"[DEBUG PDF_PROCESSOR] Q&A length: {len(q_a_transcript)}")
        print(f"[DEBUG PDF_PROCESSOR] Q&A exists: {bool(q_a_transcript)}")

        if presentation_transcript:
            print(
                f"[DEBUG PDF_PROCESSOR] Presentation preview: {presentation_transcript[:200]}...")

        if q_a_transcript:
            print(
                f"[DEBUG PDF_PROCESSOR] Q&A preview: {q_a_transcript[:200]}...")
        else:
            print("[DEBUG PDF_PROCESSOR] Q&A transcript is EMPTY!")

        return {
            "presentation_transcript": presentation_transcript,
            "presentation_text_length": len(presentation_transcript),
            "q_a_transcript": q_a_transcript,
            "qa_text_length": len(q_a_transcript),
            "original_filename": saved_filename,
            "transcript_path": transcript_path
        }

    def process_pdf_bytes(self, pdf_bytes: bytes, original_filename: Optional[str] = None) -> Dict:
        """
        Process a PDF provided as in-memory bytes, without writing a temporary file.
        """
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise PDFProcessingError("Empty PDF upload")

        # Validate size
        if len(pdf_bytes) > self.max_file_size_bytes:
            size_mb = len(pdf_bytes) / (1024 * 1024)
            max_mb = self.max_file_size_bytes / (1024 * 1024)
            raise PDFProcessingError(
                f"File size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_mb}MB)"
            )

        # Open document from memory
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise PDFProcessingError(
                f"Failed to open PDF from bytes: {str(e)}")

        print("Extracting text sections...")
        #  Extract both text sections
        presentation_transcript, q_a_transcript = self.extract_text_sections(
            doc)

        print("Validating content...")
        #  Validate content
        self.validate_content(presentation_transcript)
        if q_a_transcript:  # Only validate Q&A if it exists
            self.validate_content(q_a_transcript)

    

        # DEBUG: Log extracted content details
        print(
            f"[DEBUG PDF_PROCESSOR] Processing complete for: {original_filename}")
        print(
            f"[DEBUG PDF_PROCESSOR] Presentation length: {len(presentation_transcript)}")
        print(f"[DEBUG PDF_PROCESSOR] Q&A length: {len(q_a_transcript)}")
        print(f"[DEBUG PDF_PROCESSOR] Q&A exists: {bool(q_a_transcript)}")

        if presentation_transcript:
            print(
                f"[DEBUG PDF_PROCESSOR] Presentation preview: {presentation_transcript[:200]}...")

        if q_a_transcript:
            print(
                f"[DEBUG PDF_PROCESSOR] Q&A preview: {q_a_transcript[:200]}...")
        else:
            print("[DEBUG PDF_PROCESSOR] Q&A transcript is EMPTY!")

        doc.close()


        return {
            "presentation_transcript": presentation_transcript.strip(),
            "presentation_text_length": len(presentation_transcript),
            "q_a_transcript": q_a_transcript.strip(),
            "qa_text_length": len(q_a_transcript),
            "original_filename": (Path(original_filename or "transcript.pdf").name),
        }


def create_pdf_processor(max_file_size_mb: int = 10, save_transcripts_dir: str = "transcripts") -> PDFProcessor:
    """
    Main function to  create the pdf processor's instance
    """

    return PDFProcessor(max_file_size_mb, save_transcripts_dir)
