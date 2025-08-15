# Inputs hardcoded para a V1
CALL_TYPE = "earnings"        # "earnings" ou "conference"
SUMMARY_LENGTH = "short"      # "short" ou "long"
PDF_PATH = r"C:\Users\innyw\OneDrive - minerva.edu\kapitalo\financial-summarizer\monday.com Ltd., Q2 2025 Earnings Call, Aug 11, 2025 – monday.com Ltd. – BamSEC.pdf"
LONG_Q_A_PROMPT_VERSION = "version_2"
SHORT_Q_A_PROMPT_VERSION = "version_5"
JUDGE_PROMPT_VERSION = "version_1"
OVERVIEW_PROMPT_VERSION = "version_1"

JUDGE_MODEL = "gpt-5"
Q_A_MODEL = "gpt-5"
OVERVIEW_MODEL = "gpt-5-mini"
# Config do PDFProcessor
MAX_FILE_SIZE_MB = 10
TRANSCRIPTS_DIR = "transcripts"
