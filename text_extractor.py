import os
from PyPDF2 import PdfReader
from docx import Document

def extract_text(path):
    ext = os.path.splitext(path)[1].lower()
    
    try:
        if ext in [".txt", ".md", ".log"]:
            return open(path, "r", encoding="utf-8", errors="ignore").read()

        elif ext in [".py", ".js", ".ts", ".java"]:
            return extract_code(path)

        elif ext == ".pdf":
            return extract_pdf(path)

        elif ext == ".docx":
            return extract_docx(path)

        else:
            return None
    except:
        return None


def extract_code(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    lines = code.split("\n")
    funcs = [l for l in lines if "def " in l or "function" in l]
    return "\n".join(funcs + lines[:50])  


def extract_pdf(path):
    reader = PdfReader(path)
    texts = [page.extract_text() for page in reader.pages]
    return "\n".join([t for t in texts if t])


def extract_docx(path):
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs])
