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

import os
from flask import Blueprint, render_template
from flask_login import login_required

from app.core.config import settings

index_routes = Blueprint("index", __name__, url_prefix=settings.SERVICE_BASE_ENDPOINT)
index_routes.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template/')

@index_routes.route('/', methods=['GET'])
def homepage():
    return render_template('home.html')

@index_routes.route('/account', methods=['GET'])
@login_required
def account():
    return render_template('account.html')