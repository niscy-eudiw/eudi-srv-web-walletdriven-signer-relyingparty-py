###############################################################################
# Copyright (c) 2026 European Commission
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
import functools

from flask import render_template, current_app as app, jsonify

from app.services.log_service import add_error_log


def handle_exception(e):
    app.logger.error(f"Bad request: {e}")
    return (
        render_template(
            "error.html",
            error_code="Internal Server Error",
            error="Sorry, an internal server error has occurred. Our team has been notified and is working to resolve the issue. Please try again later.",
        ),
        500,
    )

def page_not_found(e):
    app.logger.error(f"Page not found: {e}")
    return (
        render_template(
            "error.html",
            error_code="Page not found",
            error="Page not found. We're sorry, we couldn't find the page you requested.",
        ),
        404,
    )

def with_error_logging(failure_message: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                nonce = kwargs.get("nonce")
                if nonce:
                    add_error_log(nonce, failure_message)
                app.logger.error(failure_message)
                return jsonify({"error": failure_message}), 500
        return wrapper
    return decorator