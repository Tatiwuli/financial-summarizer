"""
PDF Processor module for Earnings Call Analyzer
Handles PDF validation, text extraction, and Q&A section identification
"""


import re
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from statistics import mode, StatisticsError
import fitz

from src.config.constants import QA_PATTERNS, FILESIZE, CACHE_DIR


class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors"""
    pass


class PDFProcessor:
    """Handles PDF processing operations for earnings call transcripts"""

    def __init__(self, max_file_size_mb: int = FILESIZE, save_transcripts_dir: str = CACHE_DIR):

        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.save_transcripts_dir = Path(save_transcripts_dir)
        self.save_transcripts_dir.mkdir(exist_ok=True)
        # Titles of the Q&A sections
        self.qa_patterns = QA_PATTERNS

# ------------------ FUNCTIONS UTILITIES --------

    # Find the body font size
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

    # Find the Q&A section by Q&A keywords and font size and font weight
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

                                if re.search(re.escape(pattern), line_text, flags=re.IGNORECASE):
                                    print(
                                        f"[EXTRACT Q&A] Found Q&A pattern: {pattern}")
                                    if line_font_sizes:
                                        print(
                                            f"[EXTRACT Q&A] Line font sizes: {line_font_sizes}")
                                        max_size = max(line_font_sizes)
                                        print(
                                            f"[EXTRACT Q&A] Max size: {max_size}")
                                        # Accept if strictly larger than body, or equal-size within epsilon but bold/heading-like
                                        print(
                                            f"[EXTRACT Q&A] Min title font size: {min_title_font_size}")
                                        print(
                                            f"[EXTRACT Q&A] Is bold: {is_bold}")
                                        if max_size > (min_title_font_size) or (max_size == min_title_font_size and is_bold):
                                            print(
                                                f"[EXTRACT Q&A] Found Q&A section at page {page_num}")
                                            q_a_page_num = page_num
                                            return q_a_page_num
                                        elif max_size == min_title_font_size:
                                            # Remove the matched pattern and count remaining words
                                            remaining_text = re.sub(
                                                re.escape(pattern), "", line_text, flags=re.IGNORECASE)
                                            other_words = re.findall(
                                                r"\b\w+\b", remaining_text)
                                            print(
                                                f"[EXTRACT Q&A] Remaining words after removing pattern: {other_words}")
                                            if len(other_words) <= 3:
                                                print(
                                                    f"[EXTRACT Q&A] Accepted (equal size, <=3 other words) at page {page_num}")
                                                q_a_page_num = page_num
                                                return q_a_page_num
                                            else:
                                                print(
                                                    f"[EXTRACT Q&A] Rejected (equal size, >3 other words) at page {page_num}")

            return None

        except Exception as e:
            raise PDFProcessingError(f"Failed to find Q&A section: {str(e)}")

    def extract_text_sections(self, doc: fitz.Document) -> Tuple[str, str]:

            body_font_size = self.analyze_font_styles(doc)
            print(f"[EXTRACT Q&A] Body font size: {body_font_size}")

            qa_start_page = self.find_qa_section_title(
                doc, body_font_size)
            print(f"[EXTRACT Q&A] Q&A start page: {qa_start_page}")

            presentation_transcript = ""
            q_a_transcript = ""

        try:
            # If no Q&A section is found, the whole document is the presentation.
            if qa_start_page is None:
                print(
                    "[EXTRACT Q&A] No Q&A section found - treating entire document as presentation")
                for page_num in range(len(doc)):
                    presentation_transcript += doc.load_page(
                        page_num).get_text()
            else:
                print(
                    f"[EXTRACT Q&A] Q&A section found starting at page {qa_start_page}")
                # Extract text from pages before the Q&A section
                for page_num in range(qa_start_page):
                    presentation_transcript += doc.load_page(
                        page_num).get_text()

                # Split the page where the Q&A section starts
                page = doc.load_page(qa_start_page)
                page_text = page.get_text()

                qa_start_index = -1
                lowered_page_text = page_text.lower()
                #Find the first occurece of q&a title pattern 
                for pattern in self.qa_patterns:
                  
                    found_index = lowered_page_text.find(pattern)
                    if found_index != -1: #found pattern
                        
                        if qa_start_index == -1 or found_index < qa_start_index:
                            qa_start_index = found_index

                if qa_start_index != -1: #found q_a first occurence 
                    presentation_transcript += page_text[:qa_start_index]
                    q_a_transcript += page_text[qa_start_index:]
                else:
                    # Fallback if pattern not found on page (should not happen)
                    presentation_transcript += page_text

                # Extract text from the rest of the pages for the Q&A section
                for page_num in range(qa_start_page + 1, len(doc)):
                    q_a_transcript += doc.load_page(page_num).get_text()

            # Clean up and remove possible copyright page from the end
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

                   # if the last page has text smaller than the body font size, then trim the copyright from the last page
                    if last_page_font_sizes and max(last_page_font_sizes) < body_font_size:
                        # Decide which text block to trim the copyright from
                        if q_a_transcript and q_a_transcript.strip().endswith(last_page_text):
                            q_a_transcript = q_a_transcript.strip(
                            )[:-len(last_page_text)].strip()
                            #if the trnscript doesn't have q&a, but presentation only
                        elif presentation_transcript.strip().endswith(last_page_text):
                            presentation_transcript = presentation_transcript.strip()[
                                :-len(last_page_text)].strip()

            return presentation_transcript.strip(), q_a_transcript.strip()

        except Exception as e:
            raise PDFProcessingError(
                f"Failed to extract text sections: {str(e)}")

    # ------------------ FUNCTIONS WORKFLOWS ------------------------------------------------

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

        # DEBUG: Log extracted content details
        print(
            f"[PDF_PROCESSOR] Processing complete for: {original_filename}")
        print(
            f"[PDF_PROCESSOR] Presentation length: {len(presentation_transcript)}")
        print(f"[PDF_PROCESSOR] Q&A length: {len(q_a_transcript)}")
        print(f"[PDF_PROCESSOR] Q&A exists: {bool(q_a_transcript)}")

        if presentation_transcript:
            print(
                f"[PDF_PROCESSOR] Presentation preview: {presentation_transcript[:200]}...")

        if q_a_transcript:
            print(
                f"[PDF_PROCESSOR] Q&A preview: {q_a_transcript[:200]}...")
        else:
            print("[PDF_PROCESSOR] Q&A transcript is EMPTY!")

        doc.close()

        return {
            "presentation_transcript": presentation_transcript.strip(),
            "presentation_text_length": len(presentation_transcript),
            "q_a_transcript": q_a_transcript.strip(),
            "qa_text_length": len(q_a_transcript),
        }


def create_pdf_processor(max_file_size_mb: int = FILESIZE, save_transcripts_dir: str = CACHE_DIR) -> PDFProcessor:
    """
    Main function to  create the pdf processor's instance
    """

    return PDFProcessor(max_file_size_mb, save_transcripts_dir)
