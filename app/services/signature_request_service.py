import base64, io, qrcode, json, secrets, jwt
from typing import Optional
from urllib.parse import quote, urlencode

from app.core.config import settings
from app.models.session_state import DocumentSigningOptions
from flask import current_app as app, url_for

from app.protocols.etsi_119432 import Etsi119432RequestBuilder
from app.protocols.potential import SdAuthorizationRequestBuilder
from app.repositories import db
from app.repositories.db import get_signed_data_object_from_db, get_request_object_from_db
from app.services.key_service import get_jwt_private_key, get_jwt_certificate, get_jwt_ca_certificate
from app.services.log_service import add_error_log


def create_document_signing_request(protocol_version: str, request_object_delivery: Optional[str], wallet_url: str, documents: list[DocumentSigningOptions]):
    link_to_wallet, nonce = _get_document_retrieval_params(
        wallet_url=wallet_url,
        documents=documents,
        request_object_delivery=request_object_delivery,
        protocol_version=protocol_version)
    app.logger.info(f"Retrieved link to Wallet: {link_to_wallet} with nonce: {nonce}")

    qr_img_base64 = _get_qr_code_base64(link_to_wallet)
    return link_to_wallet, qr_img_base64, nonce

def _get_document_retrieval_params(wallet_url: str, documents: list[DocumentSigningOptions], request_object_delivery: str, protocol_version: str):
    nonce = _get_nonce()

    builder = _get_request_builder(protocol_version=protocol_version, nonce=nonce, documents=documents)
    request_object, client_id = builder.build()

    if request_object_delivery == "request_uri":
        link_to_wallet = _build_request_uri_link(wallet_url=wallet_url, nonce=nonce, request_object=request_object, client_id=client_id)
    else:
        link_to_wallet = _build_direct_params_link(wallet_url=wallet_url, request_object=request_object)
    return link_to_wallet, nonce

def _get_nonce():
    return secrets.token_urlsafe(32)

def _get_request_builder(protocol_version: str, nonce: str, documents: list[DocumentSigningOptions]):
    request_builders = {
        "etsi119432": Etsi119432RequestBuilder(nonce=nonce, documents=documents),
        "previous": SdAuthorizationRequestBuilder(nonce=nonce, documents=documents),
    }
    builder = request_builders.get(protocol_version)
    if builder is None:
        app.logger.error(f"There was an error setting up the request for document signing: Unsupported protocol_version {protocol_version!r}.")
        raise ValueError(f"Unsupported protocol_version.")
    return builder

def _build_request_uri_link(wallet_url: str, nonce: str, request_object: dict, client_id: str) -> str:
    jar = _get_jar_from_request_object(request_object)
    app.logger.info("Generated the Request Object Value.")

    db.add_to_request_object_to_table(nonce, jar)
    app.logger.info("Added the request object to the database.")

    request_uri = url_for("wallet.retrieve_request_object", nonce=nonce, _external=True, _scheme=settings.SERVICE_SCHEME)
    return f"{wallet_url}?request_uri={quote(request_uri, safe='')}&client_id={client_id}"

def _get_jar_from_request_object(request_object: dict) -> str:
    private_key = get_jwt_private_key()
    certificate_chain = [get_jwt_certificate()]
    ca_certificate = get_jwt_ca_certificate()
    if ca_certificate:
        certificate_chain.append(ca_certificate)
    headers = {"x5c":certificate_chain, "typ": "application/oauth-authz-req+jwt"}
    token = jwt.encode(request_object, private_key, algorithm=settings.JWT_ALGORITHM, headers=headers)
    app.logger.info("Generated a JWT with the Request Object.")
    return token

def _build_direct_params_link(wallet_url: str, request_object: dict) -> str:
    encoded_params = {
        key: json.dumps(value) if isinstance(value, (dict, list)) else value
        for key, value in request_object.items()
    }
    return f"{wallet_url}?{urlencode(encoded_params)}"

def _get_qr_code_base64(link_to_wallet: str) -> str:
    qr_img = qrcode.make(link_to_wallet)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")

def retrieve_request_object_with_document_signing_request(nonce: str):
    try:
        request_object = get_request_object_from_db(nonce)
    except ValueError as e:
        app.logger.error(f"An error was caught while trying to retrieve the Request Object to the Database: {e}.")
        raise

    if request_object is None:
        app.logger.info(f"No Request Object found for nonce {nonce}.")
        add_error_log(nonce, "Request Object with given nonce was not found.")
        return None

    return request_object

def retrieve_signed_objects(nonce: str):
    try:
        signed_docs_list = get_signed_data_object_from_db(nonce)
    except ValueError as e:
        app.logger.error(f"An error was caught while trying to retrieve the Request Object from the Database: {e}.")
        raise Exception("It was impossible to complete the request, as there was an error accessing the database.")

    if signed_docs_list is None:
        app.logger.info(f"Signed Data Object for the request {nonce} isn't in the DB.")
        return None

    app.logger.info(f"Found {len(signed_docs_list)} Signed Data Object for the request {nonce}.")
    return signed_docs_list


