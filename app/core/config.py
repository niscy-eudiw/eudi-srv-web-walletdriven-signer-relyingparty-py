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
    SESSION_COOKIE_SAMESITE: Optional[str] = None
    SESSION_COOKIE_SECURE: bool = True

    SAMPLE_DOCUMENTS_FOLDER: str = os.getenv("SAMPLE_DOCUMENTS_FOLDER", 'sample_docs')
    LOGS_FOLDER: str = os.getenv("LOGS_FOLDER", 'logs')

    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: int = int(os.getenv("DB_PORT"))
    DB_NAME: str = os.getenv("DB_NAME")
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")

    JWT_PRIVATE_KEY_PATH: str = os.getenv("JWT_PRIVATE_KEY_PATH")
    JWT_PRIVATE_KEY_PASSWORD: str = os.getenv("JWT_PRIVATE_KEY_PASSWORD")
    JWT_CERTIFICATE_PATH: str = os.getenv("JWT_CERTIFICATE_PATH")
    JWT_CA_CERTIFICATE_PATH: str = os.getenv("JWT_CA_CERTIFICATE_PATH")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "ES256")

    SERVICE_DOMAIN: str = os.getenv("SERVICE_DOMAIN")
    SERVICE_BASE_ENDPOINT: str = os.getenv("SERVICE_BASE_ENDPOINT", "")

    WALLET_TESTER_URL: str = os.getenv("WALLET_URL")
    CLIENT_ID_SCHEME: str = "x509_san_dns"

settings = Settings()

def validate_settings(settings):
    required_files = {
        "JWT_PRIVATE_KEY_PATH": settings.JWT_PRIVATE_KEY_PATH,
        "JWT_CERTIFICATE_PATH": settings.JWT_CERTIFICATE_PATH,
        "JWT_CA_CERTIFICATE_PATH": settings.JWT_CA_CERTIFICATE_PATH,
        "SAMPLE_DOCUMENTS_FOLDER": settings.SAMPLE_DOCUMENTS_FOLDER,
        "LOGS_FOLDER": settings.LOGS_FOLDER,
    }

    for name, path in required_files.items():
        if not path:
            raise FileNotFoundError(f"Critical Error: Required file {name} is not set")
        full_path = os.path.join(os.getcwd(), path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Critical Error: Required file ({name}) not found at '{full_path}'")



