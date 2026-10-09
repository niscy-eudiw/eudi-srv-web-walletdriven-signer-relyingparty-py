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
    conformance_level: Literal["AdES-B-B", "AdES-B-T", "AdES-B-LT", "AdES-B-LTA", "AdES-B", "AdES-T", "AdES-LT", "AdES-LTA"]

    container:  Literal["No", "ASiC-S", "ASiC-E"]
    packaging: Literal["Detached", "Attached", "Parallel",
                       "Certification", "Revision", 
                       "Enveloped", "Enveloping"]
    url: str