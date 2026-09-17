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

import os, mimetypes

from flask import (
    Blueprint, render_template, request, send_from_directory, current_app as app, Response, jsonify, url_for
)
from flask_login import login_required
from pydantic import ValidationError

from app.core.config import settings
import app.repositories.db as db
from app.models.session_state import SessionState, DocumentSigningOptions
from app.schemas.documents_routes_schemas import SigningOptions, WalletOptions
from app.services.document_service import get_document_content_base64, add_suffix_to_filename, get_document_path
from app.services.signature_request_service import retrieve_signed_objects, create_document_signing_request
from app.utils.session import update_session_values, get_session_value, clear_session

documents_routes = Blueprint("documents", __name__, url_prefix=settings.SERVICE_BASE_ENDPOINT +"/document")
documents_routes.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template/')

@documents_routes.route('/select', methods=['GET'])
@login_required
def select_document():
    clear_session()
    predefined_files = []

    try:
        files = os.listdir(settings.SAMPLE_DOCUMENTS_FOLDER)
    except OSError as e:
        app.logger.error(f"Failed to list sample documents folder: {e}")
        return jsonify({"error": "Failed to load sample documents"}), 400

    for file in files:
        try:
            data = get_document_content_base64(file)
            mimetype, _ = mimetypes.guess_type(file)
            predefined_files.append({"name": file, "data": data, "type": mimetype})
        except Exception as e:
            app.logger.error(f"Failed to read {file}: {e}")
            continue
    return render_template('document-select.html', received_files=predefined_files)

@documents_routes.route('/select', methods=['POST'])
@login_required
def select_signing_options():
    app.logger.info("Received documents to sign and signing options")
    options = request.form.getlist("options")

    if len(options) != 1:
        return jsonify({"error": "Currenty only one document can be signed at a time"}, 400)

    documents_signature_option = []
    for option in options:
        try:
            signing_options = SigningOptions.model_validate_json(option)
            url = url_for('documents.serve_docs', filename=signing_options.filename, _external=True, _scheme=settings.SERVICE_SCHEME)
            documents_signature_option.append(
                DocumentSigningOptions(
                    filepath=get_document_path(signing_options.filename),
                    filename=signing_options.filename,
                    signature_format=signing_options.signature_format,
                    conformance_level=signing_options.level,
                    container=signing_options.container,
                    packaging=signing_options.packaging,
                    url=url
                )
            )
        except Exception as e:
            app.logger.error(f"Rejected malformed signing options: {e}")
            return jsonify({"error": "Invalid signing options provided"}, 400)

    update_session_values(SessionState.DOCUMENTS_OPTIONS_TO_SIGN, documents_signature_option)
    return jsonify({"status": "ok"}), 200

@documents_routes.route("/sign", methods=['GET'])
@login_required
def select_wallet_options():
    return render_template('wallet-select.html')

# Sign with Wallet Tester for development purposes
@documents_routes.route("/sign/tester", methods=['GET'])
@login_required
def sign_with_wallet_tester():
    wallet_url = settings.WALLET_TESTER_URL
    link_to_wallet, qr_img_base64, nonce = create_document_signing_request(
        protocol_version="etsi119432",
        request_object_delivery="request_uri",
        wallet_url=wallet_url,
        documents=get_session_value(SessionState.DOCUMENTS_OPTIONS_TO_SIGN)
    )
    update_session_values(SessionState.NONCE, nonce)
    return render_template('wallet-redirect.html', wallet_url=link_to_wallet, qrcode=qr_img_base64)

@documents_routes.route("/sign", methods=['POST'])
@login_required
def sign_with_wallet():
    try:
        wallet_options = WalletOptions.from_form(request.form)
    except ValidationError as e:
        app.logger.error(f"Rejected invalid wallet options: {e}")
        return jsonify({"error": "Invalid wallet options provided"}), 400

    wallet_url = _resolve_wallet_url(wallet_options)
    link_to_wallet, qr_img_base64, nonce = create_document_signing_request(
        protocol_version=wallet_options.protocol_version,
        request_object_delivery=wallet_options.request_object_delivery,
        wallet_url=wallet_url,
        documents=get_session_value(SessionState.DOCUMENTS_OPTIONS_TO_SIGN)
    )
    update_session_values(SessionState.NONCE, nonce)
    return render_template('wallet-redirect.html', wallet_url=link_to_wallet, qrcode=qr_img_base64)

def _resolve_wallet_url(wallet_options: WalletOptions) -> str:
    if wallet_options.wallet_delivery_method == "redirect":
        return wallet_options.authorization_endpoint + settings.SERVICE_DOMAIN
    else:
        return f"{settings.SERVICE_SCHEME}://{settings.SERVICE_DOMAIN}"

# Waiting for signed document from Wallet
@documents_routes.route("/signed", methods=['GET'])
@login_required
def wait_for_signed_document():
    nonce = get_session_value(SessionState.NONCE)
    app.logger.info(f"Retrieving signed document associated to the nonce: {nonce}")

    response = retrieve_signed_objects(nonce=nonce)
    if response is not None:
        app.logger.info("Successfully received signed document from Wallet.")
        return jsonify({ "status":"ready"}), 200
    else:
        app.logger.info("Signed document not received yet. Waiting for signed document...")
        return Response("Signed document not received yet.", status=404)

@documents_routes.route("/signed/view", methods=['GET'])
@login_required
def view_signed_document():
    state = request.args.get('state')
    nonce = get_session_value(SessionState.NONCE)
    if not nonce:
        return render_template("document-signed-view.html", error = "Missing nonce.", documents=None)
    app.logger.info(f"Loading signed document view for nonce: {nonce}")

    signed_docs = retrieve_signed_objects(nonce=nonce)
    if not signed_docs:
        return render_template("document-signed-view.html", error = "No signed documents found for this request.", documents=None)

    options = get_session_value(SessionState.DOCUMENTS_OPTIONS_TO_SIGN)
    data = []
    opt:DocumentSigningOptions
    for opt, doc in zip(options, signed_docs):
        new_name = add_suffix_to_filename(os.path.basename(opt.filename))
        mime_type, _ = mimetypes.guess_type(opt.filename)
        data.append({
            'document_signed_value': doc,
            'document_content_type': mime_type,
            'document_filename': new_name
        })
    db.remove_signed_data_object_with_request_id(nonce)
    return render_template("document-signed-view.html", error = None, documents=data)

@documents_routes.route('/<path:filename>', methods=['GET'])
def serve_docs(filename):
    app.logger.info("Requested the file: "+ filename)
    return send_from_directory("../"+settings.SAMPLE_DOCUMENTS_FOLDER, filename)
