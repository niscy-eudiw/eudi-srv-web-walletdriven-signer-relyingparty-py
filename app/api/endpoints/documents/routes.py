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

import os, base64, qrcode, io, mimetypes
from flask import (
    Blueprint, render_template, request, session, send_from_directory, current_app as app, Response, jsonify, url_for,
    json, abort
)
from flask_login import login_required
from app.core.config import settings
import app.services.wallet_requests_service as wallet_interaction
import app.repositories.db as db
from app.models.session_state import SessionState, DocumentsOptionsToSign
from app.schemas.routes_schemas import SigningOptions, WalletOptions
from app.services import documents_retrieval_service
from app.services.documents_manage_service import get_base64_document, get_document_content, add_suffix_to_filename, get_path
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
        abort(500)

    for file in files:
        filepath = get_path(file)
        if not os.path.isfile(filepath):
            app.logger.error(f"Failed to find document {filepath}")
            continue
        try:
            data = get_base64_document(filepath)
        except Exception as e:
            app.logger.error(f"Failed to read {filepath}: {e}")
            continue
        mimetype, _ = mimetypes.guess_type(file)
        predefined_files.append({"name": file, "data": data, "type": mimetype})
    hash_algos = [{"name": "SHA256", "oid": "2.16.840.1.101.3.4.2.1"}]
    return render_template('document-select.html', digest_algorithms=hash_algos, received_files=predefined_files)

@documents_routes.route('/select', methods=['POST'])
@login_required
def select_signing_options():
    app.logger.info("Received documents to sign and signing options")
    options = request.form.getlist("options")

    if len(options) != 1:
        return jsonify({"error": "Currenty only one document can be signed at a time"}, 400)

    if not options:
        app.logger.error("No signing options provided")
        abort(500, "No signing options provided")

    documents_signature_option = []
    for option in options:
        try:
            parsed = json.loads(option)
            signing_options = SigningOptions(**parsed)
        except Exception as e:
            app.logger.error(f"Rejected malformed signing options: {e}")
            abort(500, "Invalid signing options provided")

        documents_signature_option.append(
            DocumentsOptionsToSign(
                get_path(signing_options.filename),
                signing_options.filename,
                signing_options.container,
                signing_options.signature_format,
                signing_options.packaging,
                signing_options.level
            )
        )
    update_session_values(SessionState.DOCUMENTS_OPTIONS_TO_SIGN, documents_signature_option)

    digest_algorithm = request.form.get("digest_algorithm")
    if not digest_algorithm:
        app.logger.error("No digest algorithm provided")
        abort(500, "No digest algorithm provided")
    update_session_values(SessionState.DIGEST_ALGORITHM_OID, digest_algorithm)

    return jsonify({"status": "ok"}), 200

@documents_routes.route("/sign", methods=['GET'])
@login_required
def select_wallet_options():
    return render_template('wallet-select.html')

def start_wallet_interaction(protocol_version: str, request_object_delivery: str | None, wallet_url: str):
    documents_signature_option = get_session_value(SessionState.DOCUMENTS_OPTIONS_TO_SIGN)
    for document_options in documents_signature_option:
        document_content = get_document_content(document_options.filename)
        document_options.update_content(content=document_content)
        url = url_for('documents.serve_docs', filename=document_options.filename, _external=True, _scheme=settings.SERVICE_SCHEME)
        document_options.update_url(url=url)

    if protocol_version == "etsi119432":
        link_to_wallet, nonce = documents_retrieval_service.get_document_retrieval_params(
            documents_info=documents_signature_option,
            wallet_url=wallet_url,
            state=session.sid,
            request_object_delivery=request_object_delivery
        )
    else:
        hash_algorithm_oid = get_session_value(SessionState.DIGEST_ALGORITHM_OID)
        link_to_wallet, nonce = wallet_interaction.sd_retrieval_from_authorization_request(
                documents_info=documents_signature_option,
                hash_algorithm_oid=hash_algorithm_oid,
                wallet_url=wallet_url,
                client_id_scheme = "x509_san_dns"
            )
    app.logger.info(f"Retrieved link to Wallet: {link_to_wallet} with nonce: {nonce}")

    retrieve_signed_document_url = url_for('documents.wait_for_signed_document', nonce=nonce)
    # Render HTML page with QrCode
    qr_img = qrcode.make(link_to_wallet)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    qr_img_base64 = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")
    return render_template('wallet-redirect.html', url=link_to_wallet, qrcode=qr_img_base64, retrieve_signed_document_url=retrieve_signed_document_url, nonce=nonce)

# Sign with Wallet Tester for development purposes
@documents_routes.route("/sign/tester", methods=['GET'])
@login_required
def sign_with_wallet_tester():
    wallet_url = settings.WALLET_TESTER_URL
    return start_wallet_interaction("previous", None, wallet_url)

@documents_routes.route("/sign", methods=['POST'])
@login_required
def sign_with_wallet():
    try:
        wallet_options = WalletOptions.from_form(request.form)
    except ValueError as e:
        app.logger.error(f"Rejected invalid wallet options: {e}")
        abort(500, description=str(e))

    if wallet_options.wallet_delivery_method == "redirect":
        wallet_url = wallet_options.authorization_endpoint + settings.SERVICE_DOMAIN
    else:
        wallet_url = settings.SERVICE_SCHEME + "://" + settings.SERVICE_DOMAIN
    return start_wallet_interaction(wallet_options.protocol_version, wallet_options.request_object_delivery, wallet_url)


# Waiting for signed document from Wallet
@documents_routes.route("/signed", methods=['GET'])
@login_required
def wait_for_signed_document():
    nonce = request.args.get('nonce')
    app.logger.info(f"Retrieving signed document associated to the nonce: {nonce}")

    response = wallet_interaction.retrieve_signed_objects(nonce=nonce)
    if response is not None:
        app.logger.info("Successfully received signed document from Wallet.")
        db.remove_request_object_with_request_id(nonce)
        return jsonify({ "status":"ready"}), 200
    else:
        app.logger.info("Signed document not received yet. Waiting for signed document...")
        return Response("Signed document not received yet.", status=404)

@documents_routes.route("/signed/view", methods=['GET'])
@login_required
def view_signed_document():
    nonce = request.args.get('nonce')
    if not nonce:
        return render_template("document-signed-view.html", error = "Missing nonce.", documents=None)

    app.logger.info(f"Loading signed document view for nonce: {nonce}")

    signed_docs = wallet_interaction.retrieve_signed_objects(nonce=nonce)
    if not signed_docs:
        return render_template("document-signed-view.html", error = "No signed documents found for this request.", documents=None)

    options = get_session_value(SessionState.DOCUMENTS_OPTIONS_TO_SIGN)
    data = []
    opt:DocumentsOptionsToSign
    for opt, doc in zip(options, signed_docs):
        filename = opt.filename
        new_name = add_suffix_to_filename(os.path.basename(filename))
        mime_type, _ = mimetypes.guess_type(filename)
        data.append({
            'document_signed_value': doc,
            'document_content_type': mime_type,
            'document_filename': new_name
        })
    return render_template("document-signed-view.html", error = None, documents=data)

# Retrieve document with given name
@documents_routes.route('/<path:filename>', methods=['GET'])
def serve_docs(filename):
    app.logger.info("Requested the file: "+ filename)
    return send_from_directory("../"+settings.SAMPLE_DOCUMENTS_FOLDER, filename)
