import base64, os
from app.core.config import settings
from pathlib import Path
from flask import current_app as app

def get_document_path(filename: str) -> Path:
    filename = Path(filename).name
    path = Path(settings.SAMPLE_DOCUMENTS_FOLDER) / filename
    if not os.path.isfile(path):
        app.logger.warning(f"Document {filename} not found in folder {settings.SAMPLE_DOCUMENTS_FOLDER}.")
        raise FileNotFoundError(f"Failed to find document {path}")
    return path

def get_document_content(filename: str) -> bytes:
    file_path = get_document_path(filename)
    with open(file_path, 'rb') as document:
        return document.read()

def get_document_content_base64(filename: str) -> str:
    document_content = get_document_content(filename)
    return base64.b64encode(document_content).decode("utf-8")

def add_suffix_to_filename(filename: str, suffix: str = "_signed") -> str:
    if not filename:
        raise ValueError("The filename cannot be empty.")
    name, ext = os.path.splitext(filename)
    return f"{name}{suffix}{ext}"