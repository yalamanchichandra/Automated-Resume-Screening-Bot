from processing.pdf_reader import extract_text_from_pdf
from processing.docx_reader import extract_text_from_docx

def load_resume_text(path):
    if path.lower().endswith(".pdf"):
        return extract_text_from_pdf(path)

    if path.lower().endswith(".docx"):
        return extract_text_from_docx(path)

    if path.lower().endswith(".txt"):
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()

    raise ValueError("Unsupported resume format")