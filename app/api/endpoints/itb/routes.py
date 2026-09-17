from flask import Blueprint, url_for, Response, jsonify

from app.core.config import settings
from app.models.session_state import DocumentSigningOptions
from app.services.document_service import get_document_path
from app.services.log_service import add_logs, get_logs
from app.services.signature_request_service import create_document_signing_request, retrieve_signed_objects

tests_routes = Blueprint("tests", __name__, url_prefix=settings.SERVICE_BASE_ENDPOINT +"/tests")

@tests_routes.route("/get", methods=["GET"])
def get_document_for_signature():
    wallet_url = f"{settings.SERVICE_SCHEME}://{settings.SERVICE_DOMAIN}"

    documents_info: list[DocumentSigningOptions] = [
        DocumentSigningOptions(
            filepath=get_document_path("sample.pdf"),
            filename="sample.pdf",
            container="No",
            signature_format="P",
            packaging="ENVELOPED",
            conformance_level="Ades-B-B",
            url= url_for('documents.serve_docs', filename="sample.pdf", _external=True, _scheme=settings.SERVICE_SCHEME)
        )
    ]

    link_to_wallet, qr_img_base64, nonce = create_document_signing_request(
        protocol_version="etsi119432",
        request_object_delivery="request_uri",
        wallet_url=wallet_url,
        documents=documents_info)
    add_logs(nonce, "Document Retrieval initialized")

    return jsonify({"qr_code": qr_img_base64, "transaction_id": nonce}), 200

@tests_routes.route("/get/<string:nonce>", methods=["GET"])
def get_signed_document(nonce):
    response = retrieve_signed_objects(nonce=nonce)
    if response is not None:
        add_logs(nonce, "Relying Party got signed document")
        return response, 200
    else:
        add_logs(nonce, "Relying Party failed to retrieve signed document")
        return Response("Signed document not received yet.", status=404)

@tests_routes.route("/logs/<string:nonce>", methods=["GET"])
def get_logs(nonce):
    return get_logs(nonce), 200
