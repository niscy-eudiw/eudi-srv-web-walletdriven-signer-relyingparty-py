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
    json
)
from flask_login import login_required
from app.core.config import settings
import app.services.wallet_requests_service as wallet_interaction
import app.repositories.db as db
from app.models.session_state import SessionState, DocumentsOptionsToSign
from app.services import documents_retrieval_service
from app.services.documents_manage_service import get_base64_document, get_document_content, add_suffix_to_filename
from app.utils.session import remove_session_values, update_session_values, get_session_value

documents_routes = Blueprint("documents", __name__, url_prefix=settings.SERVICE_BASE_ENDPOINT +"/document")
documents_routes.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template/')

@documents_routes.route('/select', methods=['GET'])
@login_required
def select_document():
    predefined_files = []
    remove_session_values(SessionState.DOCUMENTS_OPTIONS_TO_SIGN)
    remove_session_values(SessionState.DIGEST_ALGORITHM_OID)
    for file in os.listdir(settings.SAMPLE_DOCUMENTS_FOLDER):
        filepath = os.path.join(settings.SAMPLE_DOCUMENTS_FOLDER, file)
        data = get_base64_document(filepath)
        mimetype, _ = mimetypes.guess_type(file)
        predefined_files.append({"name": file, "data": data, "type": mimetype})
    hash_algos = [{"name": "SHA256", "oid": "2.16.840.1.101.3.4.2.1"}]
    return render_template('document-select.html', digest_algorithms=hash_algos, received_files=predefined_files)

def _get_path(filename: str):
    from pathlib import Path
    filename = Path(filename).name
    path = Path(settings.SAMPLE_DOCUMENTS_FOLDER) / filename
    full_path = str(os.path.join(settings.SAMPLE_DOCUMENTS_FOLDER, path))
    return full_path


@documents_routes.route('/select', methods=['POST'])
@login_required
def check():
    app.logger.info("Received documents to sign and signing options")
    options = request.form.getlist("options")
    documents_signature_option = [
        DocumentsOptionsToSign(_get_path(option["filename"]), option["filename"], option["container"], option["signature_format"], option["packaging"], option["level"])
        for option_json in options
        for option in [json.loads(option_json)]
    ]
    update_session_values(SessionState.DOCUMENTS_OPTIONS_TO_SIGN, documents_signature_option)
    update_session_values(SessionState.DIGEST_ALGORITHM_OID, request.form.get("digest_algorithm"))
    return jsonify({"status": "ok"}), 200

@documents_routes.route("/sign", methods=['GET'])
@login_required
def sca_signature_page():
    return render_template('wallet-select.html')

def start_wallet_interaction(wallet_url: str, scheme: str, version: str, how: str):
    documents_signature_option = get_session_value(SessionState.DOCUMENTS_OPTIONS_TO_SIGN)

    hash_algorithm_oid = get_session_value(SessionState.DIGEST_ALGORITHM_OID)
    for document_options in documents_signature_option:
        document_content = get_document_content(document_options.filename)
        document_options.update_content(content=document_content)
        url = url_for('documents.serve_docs', filename=document_options.filename, _external=True, _scheme=settings.SERVICE_SCHEME)
        document_options.update_url(url=url)

    if version == "etsi119432":
        link_to_wallet, nonce = documents_retrieval_service.get_document_retrieval_params(
            documents_info=documents_signature_option,
            wallet_url=wallet_url,
            redirect_uri="",
            state=session.sid
        )
    elif version == "previous":
        link_to_wallet, nonce = wallet_interaction.sd_retrieval_from_authorization_request(
                documents_info=documents_signature_option,
                hash_algorithm_oid=hash_algorithm_oid,
                wallet_url=wallet_url,
                client_id_scheme = scheme
            )
    else:
        raise Exception("Unknown Version")
    app.logger.info(f"Retrieved link to Wallet: {link_to_wallet} with nonce: {nonce}")
    
    retrieve_signed_document_url = url_for('documents.wait_for_signed_document', nonce=nonce)
    # Render HTML page with QrCode
    qr_img = qrcode.make(link_to_wallet)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    qr_img_base64 = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")
    return render_template('wallet-redirect.html', url=link_to_wallet, qrcode=qr_img_base64, retrieve_signed_document_url=retrieve_signed_document_url)

# Sign with Wallet Tester for development purposes
@documents_routes.route("/sign/tester", methods=['GET'])
@login_required
def sign_with_wallet_tester():
    wallet_url = settings.WALLET_TESTER_URL
    return start_wallet_interaction(wallet_url, "x509_san_dns", "previous", "")

@documents_routes.route("/sign", methods=['POST'])
@login_required
def sign_with_wallet():
    options = request.form
    how = options.get("redirect")
    endpoint = options.get("endpoint")
    version = options.get("version")
    wallet_url = endpoint + settings.SERVICE_DOMAIN
    return start_wallet_interaction(wallet_url, "x509_san_dns", version, how)

# Waiting for signed document from Wallet
@documents_routes.route("/signed", methods=['GET'])
@login_required
def wait_for_signed_document():
    nonce = request.args.get('nonce')
    app.logger.info(f"Retrieving signed document associated to the nonce: {nonce}")

    response = wallet_interaction.retrieve_signed_objects(nonce=nonce)
    if response is not None:
        signed_document = response
        app.logger.info("Successfully received signed document from Wallet.")
        form_list = session.get("form_global")
        data = []
        for form, doc in zip(form_list, signed_document):
            filename = form.get("filename")
            app.logger.info(f"Found the filename to sign {filename} and the expected signed document.")

            container = form.get("container")
            format = form.get("signature_format")
            packaging = form.get("packaging")
            level = form.get("level")


            new_name = add_suffix_to_filename(os.path.basename(filename))
            mime_type, _ = mimetypes.guess_type(filename)
            info = {
                'document_signed_value': doc,
                'document_content_type': mime_type,
                'document_filename': new_name
            }
            data.append(info)
        db.remove_request_object_with_request_id(nonce)
        remove_session_values("form_global")
        app.logger.info("Returning signed documents.")
        return jsonify(data)
    else:
        app.logger.info("Signed document not received yet. Waiting for signed document...")
        return Response("Signed document not received yet.", status=404)

# Retrieve document with given name
@documents_routes.route('/<path:filename>', methods=['GET'])
def serve_docs(filename):
    app.logger.info("Requested the file: "+ filename)
    return send_from_directory("../"+settings.SAMPLE_DOCUMENTS_FOLDER, filename)
