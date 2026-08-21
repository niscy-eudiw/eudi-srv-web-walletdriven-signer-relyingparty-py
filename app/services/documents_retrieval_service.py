import base64
import hashlib
import json
import secrets
from urllib.parse import quote

import jwt
from flask import url_for

from app.core.config import settings
from app.models.session_state import DocumentsOptionsToSign
from app.repositories import db
from app.services import keys_service


def get_document_retrieval_params(wallet_url: str, redirect_uri: str, state: str, documents_info: list[DocumentsOptionsToSign]):
    nonce = secrets.token_urlsafe(32)
    response_uri = url_for("wallet.place_signed_document", nonce=nonce, _external=True)
    credential_id = "xyz123"
    client_id = settings.CLIENT_ID_SCHEME+":"+settings.SERVICE_DOMAIN
    request_object = {
        "response_type":"vp_token",
        "response_mode":"direct_post",
        "client_id": client_id,
        "redirect_uri":redirect_uri,
        "state":state,
        "nonce":nonce,
        "dcql_query":get_dqcl_query(credential_id),
        "transaction_data":[_get_transaction_data(documents_info, credential_id, response_uri)]
    }

    try:
        jar = get_jar_from_request_object(request_object)
    except ValueError:
        raise Exception("It was impossible to complete the request, as there was an error generating the JWT.")

    try:
        db.add_to_request_object_to_table(nonce, jar)
    except ValueError as e:
        raise Exception("It was impossible to complete the request, as there was an error accessing the database.")

    request_uri = url_for("wallet.retrieve_request_object", nonce=nonce, _external=True)
    request_uri_url_encoded = quote(request_uri, safe="")

    link_to_wallet = wallet_url + "?request_uri=" + request_uri_url_encoded + "&client_id=" + client_id
    return link_to_wallet, nonce

def get_jar_from_request_object(request_object):
    private_key = keys_service.get_jwt_private_key()
    certificate_chain = []
    leaf_certificate = keys_service.get_jwt_certificate()
    certificate_chain.append(leaf_certificate)
    ca_certificate = keys_service.get_jwt_ca_certificate()
    certificate_chain.append(ca_certificate)
    headers = {"x5c":certificate_chain}
    token = jwt.encode(request_object, private_key, algorithm=settings.JWT_ALGORITHM, headers=headers)
    return token



def get_dqcl_query(credential_id: str):
    return {
        "credentials": [{
            "id": credential_id,
            "format": "https://cloudsignatureconsortium.org/2025/x509",
            #"meta": { # X509MetadataQuery
            #    "certificatePolicies": ["0.4.0.2042.1", "0.4.0.194112.1"]
            #}
        }]
    }

def _get_transaction_data(documents_info: list[DocumentsOptionsToSign], credential_id: str, response_uri: str) -> str:
    transaction_data = {
        "type": "https://cloudsignatureconsortium.org/2025/qes",
        "credential_ids": [credential_id],
        "signatureRequests": _get_signature_requests_document_reference(documents_info, response_uri),
    }
    return base64.urlsafe_b64encode(json.dumps(transaction_data).encode("utf-8")).rstrip(b'=').decode("utf-8")

"According to ETSI TS 119 432 1.3.1, any signatureRequest object shall include one of the following objects:"
"- documentData as specified in clause 8.1 of CSC DM"
"- documentReference as specified in clause 8.3 of CSC DM"
def _get_signature_requests_document_reference(documents_info: list[DocumentsOptionsToSign], response_uri: str) -> list:
    signature_requests = []
    for document in documents_info:
        filename = document.filename
        content = document.content
        signature_requests.append(
            {
                "label": filename,
                "access": { "type": "public" },
                "href": document.url,
                "checksum": {
                    "value": _get_checksum_value(content),
                    "algorithmOID": "2.16.840.1.101.3.4.2.1"
                },
                "signature_format": document.signature_format,
                "conformance_level": document.level,
                "signed_envelope_property": document.packaging,
                "signAlgo": "1.2.840.10045.4.3.2",
                "signatureQualifier": "eu_eidas_qes",
                "responseURI": response_uri
            }
        )

    return signature_requests

def _get_checksum_value(document_content: bytes) -> str:
    hasher = hashlib.new("sha256")
    hasher.update(document_content)
    return base64.b64encode(hasher.digest()).decode("utf-8")

def _get_signature_requests_document_data(documents_info: list[DocumentsOptionsToSign], response_uri: str) -> list:
    signature_requests = []
    for document in documents_info:
        filename = document.filename
        content = base64.b64encode(document.content)
        signature_requests.append(
            {
                "label": filename,
                "document": content,
                "documentType": "sod",
                "signature_format": document.signature_format,
                "conformance_level": document.level,
                "signed_envelope_property": document.packaging,
                "signAlgo": "1.2.840.10045.4.3.2",
                "signatureQualifier": "eu_eidas_qes",
                "responseURI": response_uri
            }
        )
    return signature_requests