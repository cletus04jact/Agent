import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

# Dummy store — replace with Redis in prod
otp_store = {}

def authenticate_user(user_id: int, password: str) -> bool:
    # TODO: Replace with hashed password logic
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=%s AND is_active=TRUE", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return bool(user)

def verify_otp_and_create_session(user_id: int, otp: str) -> int | None:
    return user_id if otp_store.get(user_id) == otp else None
