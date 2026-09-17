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
from contextlib import contextmanager

import pymysql
from app.core.config import settings
from flask import current_app as app

_sd_has_created_at: bool = False
_sdo_has_created_at: bool = False

def _get_db_connection():
    try:
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        return connection
    except pymysql.Error as e:
        app.logger.error(f"Error connecting to MariaDB: {e}")
        raise ValueError("Impossible to use database.") from e
    except (AttributeError, TypeError) as e:
        app.logger.error(f"Invalid DB configuration: {e}")
        raise ValueError("Invalid database configuration.") from e

@contextmanager
def _db_cursor(commit=False):
    connection = _get_db_connection()
    try:
        cursor = connection.cursor()
        try:
            yield cursor
            if commit:
                connection.commit()
        finally:
            cursor.close()
    finally:
        connection.close()

# The function 'add_to_signer_document_table' allows to save a given Request Object (JWT) to the Database.
# It associates the Request Object to the 'request_id'.
# It returns a ValueError if a connection to the table defined in the config file can't be established.
def add_to_request_object_to_table(request_id: str, request_object: str) -> None:
    with _db_cursor(commit=True) as cursor:
        cursor.execute(''' INSERT INTO sd (request_id, request_object) VALUES(%s,%s)''',(request_id, request_object))
    app.logger.info(f"Saved the Request Object in the database for the request {request_id}")

# The function 'get_request_object_from_db' allows to retrieve the Request Object (JWT) from the Database.
# It retrieves the Request Object associated to the 'request_id'
# It returns an ValueError if a connection to the table defined in the config file can't be established.
def get_request_object_from_db(request_id: str):
    with _db_cursor() as cursor:
        cursor.execute(''' SELECT request_object FROM sd WHERE request_id = %s''',(request_id, ))
        data = cursor.fetchone()
    if data is not None:
        app.logger.info(f"Found the Request Object for the request {request_id}.")
        return data[0]

    app.logger.info(f"No Request Object was found in the database for the request {request_id}.")
    return None

def exists_request_object_with_request_id(request_id: str) -> bool:
    with _db_cursor() as cursor:
        cursor.execute(''' SELECT request_object FROM sd WHERE request_id = %s''', (request_id, ))
        number_entries_found = cursor.rowcount
    app.logger.info(f"{number_entries_found} Request Objects were found in the database for the request {request_id}")
    return number_entries_found > 0

def remove_request_object_with_request_id(request_id: str) -> None:
    with _db_cursor(commit=True) as cursor:
        cursor.execute(''' DELETE FROM sd WHERE request_id = %s''', (request_id,))
    app.logger.info(f"Removed the Request Object from the database for the request {request_id}.")

# The function 'add_to_signed_data_object_table' allows to save the Signed Data Object in the Database.
# It associates the Signed Data Object to the 'request_id'
# It returns a ValueError if a connection to the table defined in the config file can't be established.
def add_to_signed_data_object_table(request_id: str, signed_data_objects, error: str) -> None:
    with _db_cursor(commit=True) as cursor:
        if isinstance(signed_data_objects, list) and signed_data_objects:
            for sdo in signed_data_objects:
                cursor.execute(''' INSERT INTO sdo (request_id, signed_data_object, error) VALUES(%s,%s,%s)''',(request_id, sdo, error))
            app.logger.info(f"Saved the Signed Data Object in the database for the request {request_id}.")
        else:
            cursor.execute(''' INSERT INTO sdo (request_id, signed_data_object, error) VALUES(%s,%s,%s)''',(request_id, signed_data_objects, error))
            app.logger.info(f"Saved the Signed Data Object in the database for the request {request_id}.")

def remove_signed_data_object_with_request_id(request_id: str) -> None:
    with _db_cursor(commit=True) as cursor:
        cursor.execute(''' DELETE FROM sdo WHERE request_id = %s''', (request_id,))
    app.logger.info(f"Removed the Signed Data Object from the database for the request {request_id}.")

# The function 'get_signed_data_object_from_db' allows to retrieve the Signed Data Object (signed sample_docs) from the Database.
# It retrieves the Request Object associated to the 'request_id'
# It returns an ValueError if a connection to the table defined in the config file can't be established.
def get_signed_data_object_from_db(request_id: str):
    with _db_cursor() as cursor:
        cursor.execute(''' SELECT signed_data_object FROM sdo WHERE request_id = %s''', (request_id,))
        data = cursor.fetchall()

    if data:
        app.logger.info(f"Found {len(data)} Signed Data Object in the database for the request {request_id}.")
        return data
    else:
        app.logger.info(f"No Signed Data Object was found in the database for the request {request_id}.")
        return None

def _column_exists(cursor, table_name: str, column_name: str) ->bool:
    cursor.execute(
        """SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name = %s""", (settings.DB_NAME, table_name, column_name)
    )
    return cursor.fetchone()[0] > 0

def init_db_schema_flags() -> None:
    global _sd_has_created_at, _sdo_has_created_at
    with _db_cursor() as cursor:
        _sd_has_created_at = _column_exists(cursor, "sd", "created_at")
        _sdo_has_created_at = _column_exists(cursor, "sdo", "created_at")

    if not _sd_has_created_at:
        app.logger.warning("Table 'sd' has no 'created_at' column - expired-entry cleanup will skip it.")
    if not _sdo_has_created_at:
        app.logger.warning("Table 'sdo' has no 'created_at' column - expired-entry cleanup will skip it.")

def delete_expired_entries(max_age_seconds):
    with _db_cursor(commit=True) as cursor:
        if _sd_has_created_at:
            cursor.execute('''DELETE FROM sd WHERE created_at < (UTC_TIMESTAMP() - INTERVAL %s SECOND)''', (max_age_seconds, ))
            deleted_sd = cursor.rowcount
        if _sdo_has_created_at:
            cursor.execute('''DELETE FROM sdo WHERE created_at < (UTC_TIMESTAMP() - INTERVAL %s SECOND)''', (max_age_seconds,))
            deleted_sdo = cursor.rowcount
    return deleted_sd, deleted_sdo