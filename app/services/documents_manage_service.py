import base64, os
from app.core.config import settings

def get_base64_document(filepath: str):
    base64_document = None
    with open(filepath, 'rb') as document:
        base64_document = base64.b64encode(document.read()).decode("utf-8")
    return base64_document

def get_document_content(filename) -> bytes:
    file_path = os.path.join(settings.SAMPLE_DOCUMENTS_FOLDER, filename)
    if not os.path.isfile(file_path):
        raise Exception(f"File '{filename}' not found in the sample_docs directory")
    with open(file_path, 'rb') as document:
        document_content = document.read()
    return document_content

def add_suffix_to_filename(filename, suffix="_signed"):
    name, ext = os.path.splitext(filename)
    return f"{name}{suffix}{ext}"