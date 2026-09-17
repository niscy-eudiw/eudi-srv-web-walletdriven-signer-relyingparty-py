# coding: latin-1
###############################################################################
# Copyright (c) 2025 European Commission
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
import os
from datetime import timedelta
from typing import Optional

"""
This config.py contains configuration data.
"""

class Settings:
    ENV: str = os.getenv("ENV", "dev")

    SECRET_KEY: str = os.getenv("SECRET_KEY")
    SESSION_TYPE: str = "filesystem"
    SESSION_FILE_THRESHOLD: int = 50
    SESSION_PERMANENT: bool = False
    SESSION_USE_SIGNER: bool = True
    SESSION_KEY_PREFIX: str = "wallet-driven-session:"
    SESSION_COOKIE_NAME: str = "relying-party-session"
    SESSION_COOKIE_PATH: str = "/rp"
    SESSION_COOKIE_SAMESITE: Optional[str] = "Lax"
    SESSION_COOKIE_SECURE: bool = True

    SAMPLE_DOCUMENTS_FOLDER: str = os.getenv("SAMPLE_DOCUMENTS_FOLDER", 'sample_docs')
    LOGS_FOLDER: str = os.getenv("LOGS_FOLDER", 'logs')

    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: int = int(os.getenv("DB_PORT"))
    DB_NAME: str = os.getenv("DB_NAME")
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_ENTRY_MAX_AGE_SECONDS: str = os.getenv("DB_ENTRY_MAX_AGE_SECONDS")

    ACCESS_CERTIFICATE_KEY_SOURCE: str = os.getenv("ACCESS_CERTIFICATE_KEY_SOURCE", "pem")
    # Used when ACCESS_CERTIFICATE_KEY_SOURCE == "pem" (separate files)
    ACCESS_CERTIFICATE_PRIVATE_KEY_PATH: str = os.getenv("ACCESS_CERTIFICATE_PRIVATE_KEY_PATH")
    ACCESS_CERTIFICATE_PATH: str = os.getenv("ACCESS_CERTIFICATE_PATH")
    ACCESS_CERTIFICATE_CA_PATH: str = os.getenv("ACCESS_CERTIFICATE_CA_PATH")
    # Used when ACCESS_CERTIFICATE_KEY_SOURCE == "p12" (bundled files)
    ACCESS_CERTIFICATE_P12_PATH: str = os.getenv("ACCESS_CERTIFICATE_P12_PATH")
    # Shared: p12 or pem
    ACCESS_CERTIFICATE_PRIVATE_KEY_PASSWORD: str = os.getenv("ACCESS_CERTIFICATE_PRIVATE_KEY_PASSWORD", None)
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "ES256")
    REGISTRATION_CERTIFICATE: str = os.getenv("REGISTRATION_CERTIFICATE", None)

    SERVICE_DOMAIN: str = os.getenv("SERVICE_DOMAIN")
    SERVICE_BASE_ENDPOINT: str = os.getenv("SERVICE_BASE_ENDPOINT", "")
    SERVICE_SCHEME: str = os.getenv("SERVICE_SCHEME", "http")

    WALLET_TESTER_URL: str = os.getenv("WALLET_TESTER_URL")
    CLIENT_ID_PREFIX: str = "x509_hash"

settings = Settings()

def validate_settings(settings):
    if settings.ACCESS_CERTIFICATE_KEY_SOURCE == "p12":
        required_files = {
            "ACCESS_CERTIFICATE_P12_PATH": settings.ACCESS_CERTIFICATE_P12_PATH
        }
    elif settings.ACCESS_CERTIFICATE_KEY_SOURCE == "pem":
        required_files = {
            "ACCESS_CERTIFICATE_PRIVATE_KEY_PATH": settings.ACCESS_CERTIFICATE_PRIVATE_KEY_PATH,
            "ACCESS_CERTIFICATE_PATH": settings.ACCESS_CERTIFICATE_PATH,
            "ACCESS_CERTIFICATE_CA_PATH": settings.ACCESS_CERTIFICATE_CA_PATH,
        }
    else:
        raise ValueError(f"Critical Error: Unsupported ACCESS_CERTIFICATE_KEY_SOURCE: {settings.ACCESS_CERTIFICATE_KEY_SOURCE}")

    required_files.update({
        "SAMPLE_DOCUMENTS_FOLDER": settings.SAMPLE_DOCUMENTS_FOLDER,
        "LOGS_FOLDER": settings.LOGS_FOLDER,
    })

    for name, path in required_files.items():
        if not path:
            raise FileNotFoundError(f"Critical Error: Required file {name} is not set")
        full_path = os.path.join(os.getcwd(), path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Critical Error: Required file ({name}) not found at '{full_path}'")



