
from db.connection import get_connection

def verify_user_and_get_balance(account_number, aadhar_number):
    query = """
        SELECT a.account_number, a.account_type, a.current_balance, u.first_name, u.last_name
        FROM users u
        JOIN accounts a ON u.user_id = a.user_id
        WHERE a.account_number = %s AND u.aadhar_number = %s AND u.is_active = TRUE
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (account_number, aadhar_number))
    records = cursor.fetchall()
    conn.close()
    
    return records
