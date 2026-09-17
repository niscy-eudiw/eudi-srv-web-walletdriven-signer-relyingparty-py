import base64, hashlib
from flask import current_app as app, url_for

from app.core.config import settings
from app.models.session_state import DocumentSigningOptions
from app.services.document_service import get_document_content


class SdAuthorizationRequestBuilder:
    def __init__(self, nonce: str, documents: list[DocumentSigningOptions]):
        self.nonce = nonce
        self.documents = documents

    def build(self):
        return self._generate_request_object()

    def _generate_request_object(self):
        documents_digests = self._get_document_digests()
        documents_locations = self._get_document_locations()
        request_object = {
            "response_type": "sign_response",
            "client_id": settings.SERVICE_DOMAIN,
            "client_id_scheme": settings.CLIENT_ID_PREFIX,
            "response_mode": "direct_post",
            "response_uri": url_for("wallet.place_signed_document", nonce=self.nonce, _external=True, _scheme=settings.SERVICE_SCHEME),
            "nonce": self.nonce,
            "signatureQualifier": "eu_eidas_qes",
            "documentDigests": documents_digests,
            "documentLocations": documents_locations,
            "hashAlgorithmOID": "2.16.840.1.101.3.4.2.1"
        }
        app.logger.info("Formatted the Request Object.")
        return request_object, settings.SERVICE_DOMAIN

    def _get_document_digests(self):
        documents_digests = []
        for doc_info in self.documents:
            filename = doc_info.filename
            document_content = get_document_content(filename)
            hash_func = hashlib.new("sha256")
            hash_func.update(document_content)
            hash_base64_encoded = base64.b64encode(hash_func.digest()).decode("utf-8")

            documents_digests.append({
                "hash": hash_base64_encoded,
                "label": filename
            })
            app.logger.info("Calculated Document Digest of the file: " + filename)
        app.logger.info("Formatted the Document Digest with " + str(len(documents_digests)) + " documents.")
        return documents_digests

    def _get_document_locations(self):
        document_locations = []
        for info in self.documents:
            document_locations.append({
                "uri": info.url,
                "method": {
                    "type": "public"
                }
            })
        app.logger.info("Formatted the Document Locations with " + str(len(document_locations)) + " documents.")
        return document_locations

