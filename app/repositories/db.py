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

import pymysql
from app.core.config import settings
from flask import current_app as app

def get_db_connection():
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
        return None

# The function 'add_to_signer_document_table' allows to save a given Request Object (JWT) to the Database.
# It associates the Request Object to the 'request_id'.
# It returns a ValueError if a connection to the table defined in the config file can't be established.
def add_to_request_object_to_table(request_id, request_object):
    connection = get_db_connection()
    if connection is None:
        app.logger.error("impossible to use database.")
        raise ValueError("Impossible to use database.")

    cursor = connection.cursor()
    cursor.execute(''' INSERT INTO sd (request_id, request_object) VALUES(%s,%s)''',(request_id, request_object))
    connection.commit()
    cursor.close()
    app.logger.info(f"Saved the Request Object in the Database for the request {request_id}")

# The function 'get_request_object_from_db' allows to retrieve the Request Object (JWT) from the Database.
# It retrieves the Request Object associated to the 'request_id'
# It returns an ValueError if a connection to the table defined in the config file can't be established.
def get_request_object_from_db(request_id):
    connection = get_db_connection()
    if connection is None:
        app.logger.error("impossible to use database.")
        raise ValueError("Impossible to use database.")

    cursor = connection.cursor()
    cursor.execute(''' SELECT request_object FROM sd WHERE request_id = %s''',(request_id, ))
    data = cursor.fetchone()

    if data is not None:
        app.logger.info("Found the Request Object.")
        return data[0]
    else:
        app.logger.info("Request Object not found in the Database.")
        cursor.close()
        return None

def exists_request_object_with_request_id(request_id):
    connection = get_db_connection()
    if connection is None:
        app.logger.error("impossible to use database.")
        raise ValueError("Impossible to use database.")

    cursor = connection.cursor()
    cursor.execute(''' SELECT request_object FROM sd WHERE request_id = %s''', (request_id,))
    number_entries_found = cursor.rowcount
    return number_entries_found > 0

def remove_request_object_with_request_id(request_id):
    connection = get_db_connection()
    if connection is None:
        app.logger.error("impossible to use database.")
        raise ValueError("Impossible to use database.")

    cursor = connection.cursor()
    cursor.execute(''' DELETE FROM sd WHERE request_id = %s''', (request_id,))
    cursor.close()

# The function 'add_to_signed_data_object_table' allows to save the Signed Data Object in the Database.
# It associates the Signed Data Object to the 'request_id'
# It returns a ValueError if a connection to the table defined in the config file can't be established.
def add_to_signed_data_object_table(request_id, signed_data_objects, error):
    connection = get_db_connection()
    if connection is None:
        app.logger.error("impossible to use database.")
        raise ValueError("Impossible to use database.")
    cursor = connection.cursor()

    if signed_data_objects and isinstance(signed_data_objects, list):
        for sdo in signed_data_objects:
            cursor.execute(''' INSERT INTO sdo (request_id, signed_data_object, error) VALUES(%s,%s,%s)''',
                           (request_id, sdo, error))
            connection.commit()

        cursor.close()
        app.logger.info(f"Saved the Signed Data Object in the Database for the request {request_id}.")

    elif signed_data_objects is None:
        cursor.execute(''' INSERT INTO sdo (request_id, signed_data_object, error) VALUES(%s,%s,%s)''',
                       (request_id, signed_data_objects, error))
        connection.commit()
        cursor.close()
        app.logger.info(f"Saved the Signed Data Object in the Database for the request {request_id}.")

def remove_signed_data_object_with_request_id(request_id):
    connection = get_db_connection()
    if connection is None:
        app.logger.error("impossible to use database.")
        raise ValueError("Impossible to use database.")

    cursor = connection.cursor()
    app.logger.info("Removing the Signed Data Object from the Database.")
    cursor.execute(''' DELETE FROM sdo WHERE request_id = %s''', (request_id,))
    connection.commit()
    cursor.close()

# The function 'get_signed_data_object_from_db' allows to retrieve the Signed Data Object (signed sample_docs) from the Database.
# It retrieves the Request Object associated to the 'request_id'
# It returns an ValueError if a connection to the table defined in the config file can't be established.
def get_signed_data_object_from_db(request_id):
    connection = get_db_connection()
    if connection is None:
        app.logger.error("impossible to use database.")
        raise ValueError("Impossible to use database.")

    cursor = connection.cursor()
    cursor.execute(''' SELECT signed_data_object FROM sdo WHERE request_id = %s''', (request_id,))
    data = cursor.fetchall()
    
    if data:
        app.logger.info(f"Found {len(data)} Signed Data Object in the Database for the Request {request_id}.")
        cursor.close()
        return data
    else:
        cursor.close()
        return None