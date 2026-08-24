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

"""
Application Initialization File:
Handles application setup, configuration, and exception handling.
"""

import os, sys
from flask import Flask
from flask_session import Session
from flask_cors import CORS

from app.api.endpoints.main.routes import index_routes
from app.api.endpoints.auth.routes import auth_routes
from app.api.endpoints.documents.routes import documents_routes
from app.api.endpoints.wallet.routes import wallet_routes
from app.api.endpoints.dependencies import page_not_found, handle_exception
from app.core.config import settings, validate_settings
from app.core.logging import configure_logging

sys.path.append(os.path.dirname(__file__))

def create_app():
    configure_logging()
    validate_settings(settings)

    app = Flask(
        __name__,
        instance_relative_config=True,
        static_url_path='/rp/static'
    )
    app.config.from_object(settings)


    # Initialize LoginManager
    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        from app.services.user_service import UserService
        return User(user_id) if any(user['username'] == user_id for user in UserService.get_users()) else None

    Session(app)
    CORS(app, supports_credentials=True)

    # Register routes
    app.register_blueprint(index_routes)
    app.register_blueprint(auth_routes)
    app.register_blueprint(documents_routes)
    app.register_blueprint(wallet_routes)
    # Register error handlers
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, handle_exception)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run()