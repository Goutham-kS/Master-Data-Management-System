import pymysql
from flask import flash
from config import Config

def get_db_connection():
    try:
        return pymysql.connect(
            host="localhost",
            user="root",
            password="root",
            database="itemmaster",
            cursorclass=pymysql.cursors.DictCursor 
        )
    except pymysql.MySQLError as e:
        flash(f"Database connection error: {e}", "danger")
        return None
