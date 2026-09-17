import base64, hashlib, json
from flask import url_for, session, current_app as app

from app.core.config import settings
from app.models.session_state import DocumentSigningOptions
from app.services.document_service import get_document_content
from app.services.key_service import get_certificate_thumbprint


class Etsi119432RequestBuilder:
    def __init__(self, nonce: str, documents: list[DocumentSigningOptions]):
        self.nonce = nonce
        self.documents = documents
        self.credential_id =  "qes-cert-1"

    def build(self):
        return self._generate_request_object()

    def _generate_request_object(self):
        client_id = self._get_client_id()

        request_object = {
            "response_type": "vp_token",
            "response_mode": "direct_post",
            "client_id": client_id,
            "iss": client_id,
            "aud": "https://self-issued.me/v2",
            "redirect_uri": url_for('documents.view_signed_document', state=session.sid, _external=True, _scheme=settings.SERVICE_SCHEME),
            "state": session.sid,
            "nonce": self.nonce,
            **({"verifier_info": [self._get_verifier_info()]} if settings.REGISTRATION_CERTIFICATE else {}),
            "dcql_query": self._get_dcql_query(),
            "transaction_data": [self._get_transaction_data()]
        }
        app.logger.info("Formatted the Request Object.")
        return request_object, client_id

    def _get_verifier_info(self):
        return {
            "format": "registration_cert",
            "data": settings.REGISTRATION_CERTIFICATE
        }

    def _get_dcql_query(self):
        return {
            "credentials": [{
                "id": self.credential_id,
                "format": "https://cloudsignatureconsortium.org/2025/x509",
                "meta": {}
            }]
        }

    def _get_transaction_data(self) -> str:
        transaction_data = {
            "type": "https://cloudsignatureconsortium.org/2025/qes",
            "credential_ids": [self.credential_id],
            "signatureRequests": self._get_signature_requests_document_reference(),
        }
        return base64.urlsafe_b64encode(json.dumps(transaction_data).encode("utf-8")).rstrip(b'=').decode("utf-8")


    def _get_signature_requests_document_reference(self) -> list:
        response_uri = url_for("wallet.place_signed_document_json", nonce=self.nonce, _external=True, _scheme=settings.SERVICE_SCHEME)

        signature_requests = []
        for document in self.documents:
            filename = document.filename
            content = get_document_content(filename)
            signature_requests.append(
                {
                    "label": filename,
                    "access": {"type": "public"},
                    "href": document.url,
                    "checksum": {
                        "value": self._get_checksum_value(content),
                        "algorithmOID": "2.16.840.1.101.3.4.2.1"
                    },
                    "signature_format": document.signature_format,
                    "conformance_level": document.conformance_level,
                    "signed_envelope_property": document.packaging,
                    "signAlgo": "1.2.840.10045.4.3.2",
                    "signatureQualifier": "eu_eidas_qes",
                    "responseURI": response_uri
                }
            )
            app.logger.info(f"Prepared signature_request for document {document.filename}.")
        app.logger.info(f"Formatted {len(signature_requests)} signature request(s).")
        return signature_requests

    def _get_checksum_value(self, document_content: bytes) -> str:
        hasher = hashlib.new("sha256")
        hasher.update(document_content)
        return base64.b64encode(hasher.digest()).decode("utf-8")

    def _get_signature_requests_document_data(self) -> list:
        response_uri = url_for("wallet.place_signed_document_json", nonce=self.nonce, _external=True, _scheme=settings.SERVICE_SCHEME)
        signature_requests = []
        for document in self.documents:
            filename = document.filename
            content = base64.b64encode(get_document_content(filename))
            signature_requests.append(
                {
                    "label": filename,
                    "document": content,
                    "documentType": "sod",
                    "signature_format": document.signature_format,
                    "conformance_level": document.conformance_level,
                    "signed_envelope_property": document.packaging,
                    "signAlgo": "1.2.840.10045.4.3.2",
                    "signatureQualifier": "eu_eidas_qes",
                    "responseURI": response_uri
                }
            )
        return signature_requests

    def _get_client_id(self):
        if settings.CLIENT_ID_PREFIX == "x509_hash":
            original_client_id = get_certificate_thumbprint()
        elif settings.CLIENT_ID_PREFIX == "x509_san_dns":
            original_client_id = settings.SERVICE_DOMAIN
        else:
            raise ValueError("Client ID prefix not recognized")
        client_id = settings.CLIENT_ID_PREFIX + ":" + original_client_id
        return client_id

