# Inputs hardcoded para a V1
CALL_TYPE = "conference call"        # "earnings" ou "conference"
SUMMARY_LENGTH = "short"      # "short" ou "long"
PDF_PATH = r"C:\Users\innyw\OneDrive - minerva.edu\kapitalo\financial-summarizer\monday.com Ltd., Q2 2025 Earnings Call, Aug 11, 2025 – monday.com Ltd. – BamSEC.pdf"


#JUDGE
JUDGE_PROMPT_VERSION = "version_1"
JUDGE_MODEL = "gpt-5"
EFFORT_LEVEL_JUDGE = "medium" 


####Q&A SUMMARY
Q_A_MODEL = "gpt-5"
LONG_Q_A_PROMPT_VERSION = "version_2"
SHORT_Q_A_PROMPT_VERSION = "version_5"
EFFORT_LEVEL_Q_A = "medium"

####OVERVIEW 
OVERVIEW_MODEL = "gpt-5-mini"
OVERVIEW_PROMPT_VERSION = "version_1"


# Config do PDFProcessor
MAX_FILE_SIZE_MB = 10
TRANSCRIPTS_DIR = "transcripts"
