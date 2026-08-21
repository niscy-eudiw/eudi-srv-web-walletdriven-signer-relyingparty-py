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
import base64, ast, traceback
import os
import textwrap
from flask import (Blueprint, request, current_app as app, jsonify)

from app.core.config import settings
from app.repositories import db

wallet_routes = Blueprint("wallet", __name__, url_prefix=settings.SERVICE_BASE_ENDPOINT +"/wallet")
wallet_routes.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template/')

# Endpoint that allows to retrieve the Request Object (Signer's Document)
@wallet_routes.route('/sd/<string:nonce>', methods=['GET'])
def retrieve_request_object(nonce):
    app.logger.info(f"Retrieving 'Request Object' of the Request {nonce}.")
    try:
        request_object = db.get_request_object_from_db(nonce)
        app.logger.info("Retrieved the Request Object and removed it from the database.")
    except ValueError as e:
        app.logger.error(f"An error was caught while trying to save the Request Object to the Database: {e}.")
        return None, 404

    return request_object, 200

# Endpoint that allows to save signed documents as a response to signature request
@wallet_routes.route('/sd/upload/<string:nonce>', methods=['POST'])
def place_signed_document(nonce):
    app.logger.info(f"Uploading Signed Data Object for the Request {nonce}.")
    form = request.form

    if not form:
        app.logger.error("Error retrieving Signed Data Object: expected to received the signed document as a form.")
        return jsonify({"error": "Invalid request format"}), 400

    error = form.get("error")
    if error:
        app.logger.info("Error: "+error)
    state = form.get("state")
    if state:
        app.logger.info("State: "+state)

    if not db.exists_request_object_with_request_id(nonce):
        return f"The application has no record of a request associated to {nonce}", 400

    signed_data_objects = []

    app.logger.info(f"Document With Signature: {form.get('documentWithSignature')}")

    document_with_signature = retrieve_list_values_from_form_urlencoded(form, "documentWithSignature")
    docs_signed_short_debug = textwrap.shorten(str(document_with_signature), width=50, placeholder="...")
    app.logger.info(f"Retrieved the 'document_with_signature': {docs_signed_short_debug}")
    if document_with_signature is not None:
        app.logger.info("Successfully retrieved 'documentWithSignature'.")
        app.logger.info(f"Retrieved {len(document_with_signature)} signed documents.")
        for doc in document_with_signature:
            if not is_base64(doc):
                doc = base64.b64encode(doc.encode("utf-8")).decode("ascii")
            app.logger.info(doc)
            signed_data_objects.append(doc)
        app.logger.info("Successfully uploaded all the signed documents.")

    signature_object = retrieve_list_values_from_form_urlencoded(form, "signatureObject")
    signature_short_debug = textwrap.shorten(str(signature_object), width=50, placeholder="...")
    app.logger.info(f"Retrieved the 'signature_object': {signature_short_debug}")
    if signature_object is not None:
        app.logger.info("Successfully retrieved 'signatureObject'.")
        app.logger.info(f"Retrieved {len(signature_object)} signed documents.")
        for signature in signature_object:
            signed_data_objects.append(signature)
        app.logger.info("Successfully uploaded all the signed document.")

    if signature_object is None and document_with_signature is None:
        if error is None:
            error = "Upload of the Signed Data Objects failed."
        db.add_to_signed_data_object_table(nonce, None, error)
        return "It was impossible to upload the signed data objects.", 400

    try:
        db.add_to_signed_data_object_table(nonce, signed_data_objects, error)
        db.remove_request_object_with_request_id(nonce)
        return "OK", 200
    except ValueError as e:
        app.logger.error(f"An error was caught while trying to save the signed data objects to the database: {e}.")
        return "It was impossible to upload the signed data objects.", 400

def is_base64(s: str) -> bool:
    try:
        s_aux = s.strip()
        s_bytes = s_aux.encode('ascii')
        base64.b64decode(s_bytes, validate=True)
        return True
    except Exception:
        return False

def retrieve_list_values_from_form_urlencoded(form, variable_name):
    # Indexed array (e.g., var[0]=_&var[1]=_) or Bracket notation (e.g., var[]=_&var[]=_)
    variable_list = [v for k, v in form.items() if k.startswith(variable_name+'[')]
    if variable_list:
        app.logger.info("Variable "+variable_name+" received through indexed list (e.g., 'var[0]=_&var[1]=_' or 'var[]=_&var[]=_').")
        app.logger.debug(variable_list)
        return variable_list

    # Repeated keys (e.g., var=_&var=_) or Comma-separated values (e.g., var=_,_) or URLEncoded List (e.g., var=%5B_,_%5D)
    variable_list = form.getlist(variable_name)
    if variable_list:
        app.logger.info("Variable " + variable_name + " received through repeated keys (e.g., var=_&var=_ or (e.g., var=_,_) or var=%5B_,_%5D).")
        processed_list = []
        for elem in variable_list:
            if elem.startswith("[") and elem.endswith("]"):
                try:
                    parsed = ast.literal_eval(elem)
                    app.logger.info(parsed)
                    if isinstance(parsed, list):
                        app.logger.info("It is a list.")
                        for single_doc in parsed:
                            if not is_base64(single_doc):
                                single_doc = base64.b64encode(single_doc.encode("utf-8")).decode("ascii")
                            processed_list.append(single_doc)
                    else:
                        if not is_base64(str(elem)):
                            elem = base64.b64encode(elem.encode("utf-8")).decode("ascii")
                            app.logger.info(elem)
                        processed_list.append(elem)
                except Exception as exp:
                    traceback.print_exc()
                    app.logger.error(exp)
                    processed_list.append(elem) # Fallback: keep original string
            else:
                processed_list.append(elem)
        app.logger.info(processed_list)
        app.logger.info(f"Processed List Len: {len(processed_list)}")

        # Comma-separated values (e.g., var=_,_)
        csv_list = []
        for item in processed_list:
            csv_list.extend(item.split(','))
        if csv_list:
            app.logger.info("Variable " + variable_name + " received through comma-separated values.")
            app.logger.debug(f"CSC List Len: {len(csv_list)}")
            return csv_list
        return processed_list
    return None