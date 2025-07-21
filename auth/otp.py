import random
from auth.users import otp_store

def send_otp(user_id: int):
    otp = str(random.randint(100000, 999999))
    otp_store[user_id] = otp
    print(f"[DEBUG] OTP for user {user_id}: {otp}")
    # Replace with Email/SMS logic
