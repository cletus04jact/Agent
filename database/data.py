import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta


fake = Faker('en_IN') 

# Database connection parameters
DB_NAME = "bank"
DB_USER = "postgres"
DB_PASSWORD = "1234"  
DB_HOST = "localhost"
DB_PORT = "5432"

# Constants
PHONE_NUMBER = "6381174925"
BANK_NAME = "JC Bank"
COUNTRY = "India"
STATES = ["Delhi", "Maharashtra", "Tamil Nadu", "Karnataka", "Uttar Pradesh"]
CITIES = {
    "Delhi": ["New Delhi", "Gurgaon", "Noida"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"],
    "Karnataka": ["Bangalore", "Mysore", "Hubli"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi"]
}

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def insert_users(conn):
    cursor = conn.cursor()
    for _ in range(10):
        state = random.choice(STATES)
        city = random.choice(CITIES[state])
        
        cursor.execute("""
        INSERT INTO users (
            first_name, last_name, email, phone, aadhar_number, pan_number,
            date_of_birth, address, city, state, zip_code, country, credit_score
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING user_id
        """, (
            fake.first_name(),
            fake.last_name(),
            fake.unique.email(),
            PHONE_NUMBER,
            fake.unique.numerify(text='##########'),  # 12-digit Aadhar
            fake.unique.bothify(text='?????####?'),   # PAN format
            fake.date_of_birth(minimum_age=18, maximum_age=70),
            fake.street_address(),
            city,
            state,
            fake.postcode(),
            COUNTRY,
            random.randint(300, 850)
        ))
        user_id = cursor.fetchone()[0]
        conn.commit()
        yield user_id

def insert_accounts(conn, user_ids):
    cursor = conn.cursor()
    account_types = ['checking', 'savings', 'money_market', 'cd', 'ira']
    for user_id in user_ids:
        for _ in range(2): 
            cursor.execute("""
            INSERT INTO accounts (
                user_id, account_number, account_type, current_balance, available_balance
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING account_id
            """, (
                user_id,
                fake.unique.numerify(text='############'),  # 12-digit account number
                random.choice(account_types),
                round(random.uniform(1000, 100000), 2),
                round(random.uniform(1000, 100000), 2)
            ))
            account_id = cursor.fetchone()[0]
            conn.commit()
            yield account_id

def insert_transactions(conn, account_ids):
    cursor = conn.cursor()
    transaction_types = ['deposit', 'withdrawal', 'transfer', 'payment', 'fee', 'interest']
    statuses = ['pending', 'completed', 'failed', 'reversed']
    
    for account_id in account_ids:
        balance = 1000  
        for _ in range(10):
            amount = round(random.uniform(100, 10000), 2)
            transaction_type = random.choice(transaction_types)
            
            if transaction_type in ['withdrawal', 'payment', 'fee']:
                balance -= amount
            else:
                balance += amount
                
            cursor.execute("""
            INSERT INTO transactions (
                account_id, transaction_type, amount, running_balance,
                description, posted_date, status, merchant_name,
                merchant_category, reference_number, location
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                account_id,
                transaction_type,
                amount,
                balance,
                f"{BANK_NAME} {transaction_type}",
                fake.date_this_year(),
                random.choice(statuses),
                fake.company(),
                random.choice(['Retail', 'Groceries', 'Utilities', 'Entertainment']),
                fake.unique.numerify(text='TXN########'),
                fake.city()
            ))
        conn.commit()

def insert_cards(conn, user_ids, account_ids):
    cursor = conn.cursor()
    card_types = ['debit', 'credit', 'prepaid']
    card_networks = ['visa', 'mastercard', 'amex', 'discover']
    
    for user_id, account_id in zip(user_ids[:10], account_ids[:10]):  
        cursor.execute("""
        INSERT INTO cards (
            account_id, user_id, card_number, card_type, card_network,
            expiration_date, cvv, daily_limit, pin_number
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            account_id,
            user_id,
            fake.unique.numerify(text='################'),  # 16-digit card number
            random.choice(card_types),
            random.choice(card_networks),
            (datetime.now() + timedelta(days=365*3)).date(),  # 3 years from now
            fake.numerify(text='###'),
            round(random.uniform(10000, 50000), 2),
            fake.numerify(text='####')
        ))
    conn.commit()

def insert_loans(conn, user_ids, account_ids):
    cursor = conn.cursor()
    loan_types = ['personal', 'mortgage', 'auto', 'student', 'business', 'home_equity']
    
    for user_id, account_id in zip(user_ids[:5], account_ids[:5]):  # 5 loans
        amount = round(random.uniform(50000, 5000000), 2)
        term = random.choice([12, 24, 36, 60, 84])  # 1-7 years
        start_date = fake.date_this_decade()
        
        cursor.execute("""
        INSERT INTO loans (
            user_id, account_id, loan_type, loan_number, original_amount,
            current_balance, interest_rate, term_months, start_date,
            maturity_date, payment_frequency, next_payment_date,
            next_payment_amount, status, collateral_description
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            account_id,
            random.choice(loan_types),
            f"LN{fake.unique.numerify(text='########')}",
            amount,
            amount * random.uniform(0.1, 0.9), 
            round(random.uniform(7.0, 15.0), 2), 
            term,
            start_date,
            start_date + timedelta(days=term*30),  
            'monthly',
            datetime.now().date() + timedelta(days=30), 
            round(amount * 0.01, 2),  
            'active',
            fake.sentence() if random.choice([True, False]) else None
        ))
    conn.commit()

def insert_deposits(conn, user_ids, account_ids):
    cursor = conn.cursor()
    deposit_types = ['cd', 'fixed', 'recurring']
    
    for user_id, account_id in zip(user_ids[5:10], account_ids[5:10]):  
        amount = round(random.uniform(10000, 1000000), 2)
        term = random.choice([3, 6, 12, 24, 36])  
        start_date = fake.date_this_year()
        
        cursor.execute("""
        INSERT INTO deposits (
            user_id, account_id, deposit_type, deposit_number, amount,
            interest_rate, term_months, start_date, maturity_date,
            interest_payout, status, auto_renewal, early_withdrawal_penalty
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            account_id,
            random.choice(deposit_types),
            f"DP{fake.unique.numerify(text='########')}",
            amount,
            round(random.uniform(3.0, 7.5), 2),  
            term,
            start_date,
            start_date + timedelta(days=term*30),  
            random.choice(['monthly', 'quarterly', 'annually', 'at_maturity']),
            'active',
            random.choice([True, False]),
            round(random.uniform(0.5, 2.0), 2) 
        ))
    conn.commit()

def main():
    conn = get_db_connection()
    
    try:
        print("Inserting users...")
        user_ids = list(insert_users(conn))
        
        # Insert accounts and get their IDs
        print("Inserting accounts...")
        account_ids = list(insert_accounts(conn, user_ids))
        
        # Insert transactions
        print("Inserting transactions...")
        insert_transactions(conn, account_ids)
        
        # Insert cards
        print("Inserting cards...")
        insert_cards(conn, user_ids, account_ids)
        
        # Insert loans
        print("Inserting loans...")
        insert_loans(conn, user_ids, account_ids)
        
        # Insert deposits
        print("Inserting deposits...")
        insert_deposits(conn, user_ids, account_ids)
        
        print("Data insertion completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()