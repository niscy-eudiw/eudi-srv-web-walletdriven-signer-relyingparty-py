# coding: latin-1
###############################################################################
# Copyright 2025 European Commission
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###############################################################################
import base64, json, os, re
from flask import (Blueprint, request, current_app as app, jsonify)

from app.core.config import settings
from app.repositories import db
from app.services.signature_request_service import retrieve_request_object_with_document_signing_request

wallet_routes = Blueprint("wallet", __name__, url_prefix=settings.SERVICE_BASE_ENDPOINT +"/wallet")
wallet_routes.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template/')

def _is_valid_nonce(nonce: str) -> bool:
    if not bool(re.compile(r'^[A-Za-z0-9_-]{43}$').fullmatch(nonce)):
        app.logger.error(f"Rejected malformed nonce: {nonce}")
        return False
    return True

def _is_base64(s: str) -> bool:
    try:
        s_bytes = s.strip().encode('ascii')
        base64.b64decode(s_bytes, validate=True)
        return True
    except (ValueError, UnicodeEncodeError):
        return False

def _ensure_base64(value: str) -> str:
    if _is_base64(value):
        return value
    return base64.b64encode(value.encode("utf-8")).decode("ascii")

# Endpoint that allows to retrieve the Request Object (Signer's Document)
@wallet_routes.route('/sd/<string:nonce>', methods=['GET'])
def retrieve_request_object(nonce):
    if not _is_valid_nonce(nonce):
        return jsonify({"error": "Invalid request"}), 400

    request_object = retrieve_request_object_with_document_signing_request(nonce)
    if request_object is None:
        return jsonify({"error": "Request Object with document signing request not found."}), 404

    return request_object, 200

def _process_signed_data_objects(nonce, error, state, document_with_signature, signature_object):
    if error:
        app.logger.info("Error: " + error)
    if state:
        app.logger.info("State: " + state)

    if not db.exists_request_object_with_request_id(nonce):
        app.logger.error(f"No known Request Object exists for id {nonce}; rejecting signed data upload.")
        return f"The application has no record of a request associated to this id.", 400

    if signature_object is None and document_with_signature is None:
        error = error or "Upload of the Signed Data Objects failed."
        db.add_to_signed_data_object_table(nonce, None, error)
        return "It was impossible to upload the signed data objects.", 400

    signed_data_objects = []
    if document_with_signature is not None:
        app.logger.info(f"Retrieved {len(document_with_signature)} signed document(s).")
        signed_data_objects.extend(_ensure_base64(doc) for doc in document_with_signature)

    if signature_object is not None:
        app.logger.info(f"Retrieved {len(signature_object)} signed document(s).")
        signed_data_objects.extend(signature_object)

    try:
        db.add_to_signed_data_object_table(nonce, signed_data_objects, error)
        db.remove_request_object_with_request_id(nonce)
        return "OK", 200
    except ValueError as e:
        app.logger.error(f"An error was caught while trying to save the signed data objects to the database: {e}.")
        return "It was impossible to upload the signed data objects.", 400

def _finalize_signed_document_upload(nonce, error, state, document_with_signature, signature_object):
    response = _process_signed_data_objects(nonce, error, state, document_with_signature, signature_object)
    return response

# Endpoint that allows to save signed documents as a response to signature request
@wallet_routes.route('/sd/upload/<string:nonce>', methods=['POST'])
def place_signed_document(nonce):
    if not _is_valid_nonce(nonce):
        return jsonify({"error": "Invalid request"}), 400
    app.logger.info(f"Uploading Signed Data Object (form) for the Request {nonce}.")

    form = request.form
    if not form:
        app.logger.error("Error retrieving Signed Data Object for {nonce}: expected to received the signed document as a form.")
        return jsonify({"error": "Invalid request format"}), 400

    error = form.get("error")
    state = form.get("state")
    document_with_signature = retrieve_list_values_from_form_urlencoded(form, "documentWithSignature")
    signature_object = retrieve_list_values_from_form_urlencoded(form, "signatureObject")
    return _finalize_signed_document_upload(nonce, error, state, document_with_signature, signature_object)

@wallet_routes.route('/sd/upload/json/<string:nonce>', methods=['POST'])
def place_signed_document_json(nonce):
    if not _is_valid_nonce(nonce):
        return jsonify({"error": "Invalid request"}), 400
    app.logger.info(f"Uploading Signed Data Object (JSON) for the Request {nonce}.")

    if not request.is_json:
        app.logger.error("Rejected signed document upload for {nonce}: expected Content-Type application/json.")
        return jsonify({"error":"Invalid request format"}), 400

    data = request.get_json(silent=True)
    if not data:
        app.logger.error(f"Rejected signed document for {nonce}: invalid or empty JSON body.")
        return jsonify({"error": "Invalid request format"}), 400

    document_with_signature = data.get("documentWithSignature")
    signature_object = data.get("signatureObject")
    if document_with_signature is not None and not isinstance(document_with_signature, list):
        document_with_signature = [document_with_signature]
    if signature_object is not None and not isinstance(signature_object, list):
        signature_object = [signature_object]

    return _finalize_signed_document_upload(nonce, None, None, document_with_signature, signature_object)

def retrieve_list_values_from_form_urlencoded(form, variable_name: str):
    indexed = _parse_indexed_form_values(form, variable_name)
    if indexed:
        return indexed
    return _parse_repeated_or_delimited_form_values(form, variable_name)

def _parse_indexed_form_values(form, variable_name: str) -> list:
    values = [v for k, v in form.items() if k.startswith(f"{variable_name}[")]
    if values:
        app.logger.info(f"{variable_name} received via indexed/bracket list notation.")
    return values

def _parse_repeated_or_delimited_form_values(form, variable_name: str):
    raw_values = form.getlist(variable_name)
    if not raw_values:
        return None

    app.logger.info(f"{variable_name} received via repeated keys / comma-separated / encoded-list form.")
    processed = _normalize_bracket_encoded_values(raw_values, variable_name)
    return _split_comma_separated(processed)


def _normalize_bracket_encoded_values(raw_values: list, variable_name: str) -> list:
    processed = []
    for elem in raw_values:
        if elem.startswith("[") and elem.endswith("]"):
            processed.extend(_parse_json_list_element(elem, variable_name))
        else:
            processed.append(elem)
    return processed

def _parse_json_list_element(elem: str, variable_name: str) -> list:
    try:
        parsed = json.loads(elem)
    except json.JSONDecodeError:
        app.logger.error(f"Faailed to parse list-like value for {variable_name}")
        return [elem]

    if isinstance(parsed, list):
        return [_ensure_base64(item) for item in parsed]
    return [_ensure_base64(str(parsed))]

def _split_comma_separated(values: list) -> list:
    result = []
    for item in values:
        result.extend(item.split(','))
    return result