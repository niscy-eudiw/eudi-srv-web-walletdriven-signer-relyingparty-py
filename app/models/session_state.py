class SessionState:
    DEFAULT_DOCUMENTS = "default_documents"

    DOCUMENTS_OPTIONS_TO_SIGN = "documents_options_to_sign"
    DIGEST_ALGORITHM_OID = "digest_algorithm_oid"



class DocumentsOptionsToSign:
    filepath: str
    filename: str
    container: str # 'No' ou 'ASiS-C'
    signature_format: str # 'J'
    packaging: str # signed_envelope_property -> 'ENVELOPING'
    level: str # conformance_level -> 'Ades-B-B'
    content: bytes
    url: str

    def __init__(self, filepath: str, finename: str, container: str, signature_format: str, packaging: str, level: str):
        self.filepath = filepath
        self.filename = finename
        self.container = container
        self.signature_format = signature_format
        self.packaging = packaging
        self.level = level

    def update_content(self, content):
        self.content = content

    def update_url(self, url):
        self.url = url