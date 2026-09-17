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
import hashlib, base64
from pathlib import Path
from typing import Optional

from flask import current_app as app

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, pkcs12

from app.core.config import settings

class JWTKeyMaterial:
    def __init__(self, private_key, certificate, ca_certificate):
        self.private_key = private_key
        self.certificate = certificate
        self.ca_certificate = ca_certificate

_key_material: Optional[JWTKeyMaterial] = None

def init_jwt_key_material():
    global _key_material
    try:
        private_key, certificate, ca_certificate = _load_key_material()
    except Exception:
        app.logger.error("JWT key material initialization failed")
        raise
    _key_material = JWTKeyMaterial(private_key, certificate, ca_certificate)
    app.logger.info("JWT key material loaded successfully (source %s)", settings.ACCESS_CERTIFICATE_KEY_SOURCE)

def _get_key_material() -> JWTKeyMaterial:
    if _key_material is None:
        app.logger.critical("JWT key material not loaded")
        raise RuntimeError("JWT key material not initialized")
    return _key_material

def _load_key_material():
    if settings.ACCESS_CERTIFICATE_KEY_SOURCE == "p12":
        return _load_from_p12()
    elif settings.ACCESS_CERTIFICATE_KEY_SOURCE == "pem":
        return _load_from_pem_files()
    else:
        raise ValueError(f"Unsupported ACCESS_CERTIFICATE_KEY_SOURCE: {settings.ACCESS_CERTIFICATE_KEY_SOURCE!r}")

def _load_from_p12():
    p12_path = Path(settings.ACCESS_CERTIFICATE_P12_PATH)
    password = settings.ACCESS_CERTIFICATE_PRIVATE_KEY_PASSWORD.encode() if settings.ACCESS_CERTIFICATE_PRIVATE_KEY_PASSWORD else None
    try:
        with open(p12_path, "rb") as f:
            private_key, certificate, ca_certificates = pkcs12.load_key_and_certificates(
                f.read(), password, backend=default_backend()
            )
    except FileNotFoundError:
        app.logger.error("JWT P12 file not found at %s", p12_path)
        raise
    except (ValueError, TypeError):
        app.logger.error("Failed to load JWT P12: invalid password or malformed file")
        raise
    ca_certificate = ca_certificates[0] if ca_certificates else None
    return private_key, certificate, ca_certificate

def _load_from_pem_files():
    key_path = Path(settings.ACCESS_CERTIFICATE_PRIVATE_KEY_PATH)
    certificate_path = Path(settings.ACCESS_CERTIFICATE_PATH)
    ca_certificate_path = Path(settings.ACCESS_CERTIFICATE_CA_PATH)
    password = settings.ACCESS_CERTIFICATE_PRIVATE_KEY_PASSWORD.encode() if settings.ACCESS_CERTIFICATE_PRIVATE_KEY_PASSWORD else None
    try:
        with open(key_path, "rb") as f:
            private_key = _load_private_key_any_encoding(f.read(), password)
        with open(certificate_path, "rb") as f:
            certificate = _load_certificate_any_encoding(f.read())
        with open(ca_certificate_path, "rb") as f:
            ca_certificate = _load_certificate_any_encoding(f.read())
    except FileNotFoundError as e:
        app.logger.error("JWT P12 file not found at %s", e.filename)
        raise
    except (ValueError, TypeError):
        app.logger.error("Failed to load JWT P12: invalid password or malformed file")
        raise
    return private_key, certificate, ca_certificate

def _load_private_key_any_encoding(data: bytes, password):

    try:
        return serialization.load_pem_private_key(data, password=password, backend=default_backend())
    except ValueError:
        return serialization.load_der_private_key(data, password=password, backend=default_backend())

def _load_certificate_any_encoding(data: bytes):
    if not data:
        return None
    try:
        return x509.load_pem_x509_certificate(data, backend=default_backend())
    except ValueError:
        return x509.load_der_x509_certificate(data, backend=default_backend())

def get_jwt_private_key() -> str:
    return _get_key_material().private_key

def get_jwt_certificate() -> str:
    certificate= _get_key_material().certificate
    return base64.b64encode(certificate.public_bytes(encoding=Encoding.DER)).decode("utf-8")

def get_jwt_ca_certificate():
    ca_certificate = _get_key_material().ca_certificate
    if ca_certificate is None:
        return None
    return base64.b64encode(ca_certificate.public_bytes(encoding=Encoding.DER)).decode("utf-8")

def get_certificate_thumbprint() -> str:
    certificate = _get_key_material().certificate
    der_bytes = certificate.public_bytes(encoding=Encoding.DER)
    digest = hashlib.sha256(der_bytes).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

