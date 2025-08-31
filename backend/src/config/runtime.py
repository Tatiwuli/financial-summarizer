# Inputs hardcoded para a V1
CALL_TYPE = "conference call"        # "earnings" ou "conference"
SUMMARY_LENGTH = "short"      # "short" ou "long"
PDF_PATH = r"C:\Users\innyw\OneDrive - minerva.edu\kapitalo\financial-summarizer\monday.com Ltd., Q2 2025 Earnings Call, Aug 11, 2025 – monday.com Ltd. – BamSEC.pdf"


# JUDGE
JUDGE_PROMPT_VERSION = "version_1"
JUDGE_MODEL = "gpt-5"
EFFORT_LEVEL_JUDGE = "medium"


# Q&A SUMMARY EARNINGS
Q_A_MODEL = "gpt-5"
EARNINGS_LONG_Q_A_PROMPT_VERSION = "version_3"
EARNINGS_SHORT_Q_A_PROMPT_VERSION = "version_7"
EFFORT_LEVEL_Q_A = "minimal"

# CONFERENCE
CONFERENCE_Q_A_MODEL = "gpt-5"
CONFERENCE_LONG_Q_A_PROMPT_VERSION = "version_2"

EFFORT_LEVEL_Q_A_CONFERENCE = "minimal"


# OVERVIEW
OVERVIEW_MODEL = "gpt-5-mini"
OVERVIEW_PROMPT_VERSION = "version_2"


# Config do PDFProcessor
MAX_FILE_SIZE_MB = 10
TRANSCRIPTS_DIR = "local_cache"
