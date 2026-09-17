# coding: latin-1
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

import threading
from app.repositories.db import delete_expired_entries

class CleanupThread(threading.Thread):
    def __init__(self, app, max_age_seconds, internal_seconds=300):
        super().__init__(daemon=True)
        self.app = app
        self.max_age_seconds = max_age_seconds
        self.internal_seconds = internal_seconds
        self._stop_event = threading.Event()

    def run(self):
        with self.app.app_context():
            self.app.logger.info("Cleanup thread started.")
            while not self._stop_event.is_set():
                try:
                    deleted_sd, deleted_sdo = delete_expired_entries(self.max_age_seconds)
                    if deleted_sd or deleted_sdo:
                        self.app.logger.info(
                            f"Cleanup: removed {deleted_sd} expired request objects, "
                            f"{deleted_sdo} expired signed data objects."
                        )
                except Exception as e:
                    self.app.logger.error(f"Cleanup thread error: {e}")
                self._stop_event.wait(self.internal_seconds)

    def stop(self):
        self._stop_event.set()