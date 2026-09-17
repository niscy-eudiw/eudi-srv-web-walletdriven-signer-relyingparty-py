from pathlib import Path
from typing import Literal
from pydantic import BaseModel

class SessionState:
    DOCUMENTS_OPTIONS_TO_SIGN = "documents_options_to_sign"
    NONCE="nonce"

class DocumentSigningOptions(BaseModel):
    filepath: Path
    filename: str
    signature_format:  Literal["X", "P", "C", "J"]
    conformance_level: Literal["Ades-B-B", "Ades-B-T", "Ades-B-LT", "Ades-B-LTA"]

    container:  Literal["No", "ASiC-S", "ASiC-E"]
    packaging: Literal["ENVELOPED", "ENVELOPING", "DETACHED", "INTERNALLY_DETACHED"]

    url: str