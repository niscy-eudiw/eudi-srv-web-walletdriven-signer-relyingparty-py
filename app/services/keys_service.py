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

import os, base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from app.core.config import settings

def get_jwt_private_key():
    required_key = os.path.join(os.getcwd(), settings.JWT_PRIVATE_KEY_PATH)
    with open(required_key, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=settings.JWT_PRIVATE_KEY_PASSWORD.encode(),
            backend=default_backend()
        )
    return private_key

def get_jwt_certificate():
    required_certificate = os.path.join(os.getcwd(), settings.JWT_CERTIFICATE_PATH)
    with open(required_certificate, "rb") as f:
        certificate = f.read()
    base64_encoded = base64.b64encode(certificate).decode("utf-8")
    return base64_encoded

def get_jwt_ca_certificate():
    required_certificate_ca = os.path.join(os.getcwd(), settings.JWT_CA_CERTIFICATE_PATH)
    with open(required_certificate_ca, "rb") as f:
        ca_certificate = f.read()
    base64_encoded = base64.b64encode(ca_certificate).decode("utf-8")
    return base64_encoded
