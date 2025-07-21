import os
import numpy_financial as npf
from langchain.tools import tool, Tool
from langchain.tools.retriever import create_retriever_tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.messages import SystemMessage
from pathlib import Path
from google.api_core.exceptions import ResourceExhausted
import logging
from langchain.tools import tool
import psycopg2
import psycopg2
import random
import string
from datetime import date
from decimal import Decimal


# --- Loan interest rate map ---
LOAN_INTEREST_RATES = {
    "home": 7.5,
    "education": 5.0,
    "personal": 11.0,
}

CARD_INTEREST_RATES = {
    "silver": 24.0,
    "gold": 21.0,
    "platinum": 18.0,
}

# --- Tool 1: Knowledge Base (FAISS) ---
def get_retriever_tool():
    vector_store_path = Path("vectordb/faiss_index")
    
    if not vector_store_path.exists():
        raise FileNotFoundError("Vector store not found. Run indexing script to create it.")
    
    # Only embed if needed — loading from disk does NOT trigger new API calls
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        vector_store = FAISS.load_local(
            str(vector_store_path),
            embeddings,
            allow_dangerous_deserialization=True
        )
        retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    except ResourceExhausted as e:
        raise RuntimeError("Google Gemini API quota exceeded.") from e

    retriever_tool = create_retriever_tool(
        retriever,
        "knowledge_base_tool",
        "Use this to answer questions about internal banking procedures and product details."
    )
    return retriever_tool

# --- Tool 2: Loan EMI Calculator ---
@tool
def loan_payment_calculator(principal: float, years: int, loan_type: str = "personal") -> str:
    """
    Calculates EMI using built-in interest rates:
    - Home: 7.5%
    - Education: 5.0%
    - Personal: 11.0%

    Provide this tool with:
    - principal amount (in ₹)
    - duration (in years)
    - loan_type: 'home', 'education', or 'personal'

    Example: For ₹300,000 education loan over 5 years, use loan_type='education'.
    """
    try:
        rate = LOAN_INTEREST_RATES.get(loan_type.lower())
        if rate is None:
            return f"Unknown loan type '{loan_type}'. Please choose from: {', '.join(LOAN_INTEREST_RATES.keys())}"
        monthly_rate = rate / 12 / 100
        n_payments = years * 12
        monthly_payment = npf.pmt(monthly_rate, n_payments, -principal)
        return f"For a {loan_type} loan of ₹{principal:,.2f} over {years} years at {rate}% annual interest, your monthly EMI is ₹{monthly_payment:,.2f}."
    except Exception as e:
        return f"Error calculating loan payment: {e}"

# --- Tool 3: Card Bill Calculator ---
@tool
def card_bill_calculator(balance: float, months: int, card_type: str = "silver") -> str:
    """
    Calculates estimated card bill payments. Interest rate depends on card type.
    """
    try:
        rate = CARD_INTEREST_RATES.get(card_type.lower())
        if rate is None:
            return f"Unknown card type '{card_type}'. Please choose from: {', '.join(CARD_INTEREST_RATES.keys())}"
        monthly_rate = rate / 12 / 100
        total_payment = npf.pmt(monthly_rate, months, -balance)
        return f"For a {card_type} card with ₹{balance:,.2f} over {months} months at {rate}% annual interest, monthly bill is approx ₹{total_payment:,.2f}."
    except Exception as e:
        return f"Error calculating card bill: {e}"

# --- Tool 4: Web Fallback Search ---
def get_web_search_tool():
    web_search_tool = TavilySearchResults(max_results=3)
    web_search_tool.description = (
        "Use this only if the knowledge_base_tool cannot find an answer. "
        "This is a fallback for general finance terms, definitions, or uncommon features like 'reverse sweep'."
        "Always search from a **banking or financial perspective**. "
    )
    return web_search_tool


# --- Tool 5: User-Specific SQL Tool ---
def get_sql_database_tool(llm, user_id: int):
    db_uri = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@" \
             f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    db = SQLDatabase.from_uri(db_uri)
    sql_prompt = f"""
        You are a SQL agent. Only access data for user_id = {user_id}.
        Never show IDs. Answer from tables: accounts, transactions, loans, deposits, cards.
    """
    sql_agent = create_sql_agent(
        llm=llm,
        db=db,
        agent_type="tool-calling",
        verbose=True,
        extra_prompt_messages=[SystemMessage(content=sql_prompt)],
    )
    return Tool(name="customer_database_tool", func=sql_agent.invoke,
                description="Access the logged-in user's account, cards, loans, and deposits.")

@tool
def compare_loan_emis(principal: float, years: int) -> str:
    """
    Compares EMI for education vs personal loan for given principal and duration.
    Uses internal bank interest rates.
    """
    try:
        edu_rate = LOAN_INTEREST_RATES["education"]
        personal_rate = LOAN_INTEREST_RATES["personal"]

        edu_emi = npf.pmt(edu_rate / 12 / 100, years * 12, -principal)
        per_emi = npf.pmt(personal_rate / 12 / 100, years * 12, -principal)

        return (
            f"For ₹{principal:,.0f} over {years} years:\n"
            f"- Education Loan EMI @ {edu_rate}%: ₹{edu_emi:,.2f}\n"
            f"- Personal Loan EMI @ {personal_rate}%: ₹{per_emi:,.2f}\n"
            f"Education loan offers lower EMI due to reduced interest."
        )
    except Exception as e:
        return f"Error during EMI comparison: {e}"
    
#---Tool:Bank balance checker---
@tool
def get_account_balance_by_identity(account_number: str, aadhar_number: str) -> str:
    """
    Returns the user's account balance based on verified account_number and Aadhar number.
    Available only for logged-in users.
    """

    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        cursor = conn.cursor()
        query = """
            SELECT u.first_name, u.last_name, a.account_number, a.current_balance
            FROM users u
            JOIN accounts a ON u.user_id = a.user_id
            WHERE a.account_number = %s AND u.aadhar_number = %s AND u.is_active = TRUE
        """
        cursor.execute(query, (account_number, aadhar_number))
        results = cursor.fetchall()
        conn.close()

        if not results:
            return "No matching account found. Please check your details."

        response = ""
        for fname, lname, acc_num, balance in results:
            response += f"Hello {fname} {lname}, Account Number: {acc_num}, Balance: ₹{balance:,.2f}\n"
        return response.strip()
    except Exception as e:
        return f"Error accessing account balance: {e}"
    
#--Account creation tools---
@tool
def open_account_form(
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    aadhar_number: str,
    pan_number: str,
    date_of_birth: str,
    address: str,
    city: str,
    state: str,
    zip_code: str,
    country: str = "India",
    credit_score: int = 700,
    account_type: str = "savings"
) -> str:
    """
    Opens a new account in JC Bank. Asks all personal and account details step by step.
    Stores data into users and accounts tables. Account type can be 'checking', 'savings', etc.
    """

    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        cursor = conn.cursor()

        # Insert into users table
        cursor.execute("""
            INSERT INTO users (
                first_name, last_name, email, phone, aadhar_number, pan_number,
                date_of_birth, address, city, state, zip_code, country,
                credit_score, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            RETURNING user_id
        """, (
            first_name, last_name, email, phone, aadhar_number, pan_number,
            date_of_birth, address, city, state, zip_code, country,
            credit_score
        ))
        user_id = cursor.fetchone()[0]

        # Generate a unique account number
        account_number = ''.join(random.choices(string.digits, k=12))

        # Insert into accounts table
        cursor.execute("""
            INSERT INTO accounts (
                user_id, account_number, account_type,
                current_balance, available_balance, status
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            user_id, account_number, account_type,
            0.00, 0.00, 'active'
        ))

        conn.commit()
        conn.close()

        return f"🎉 Account successfully created!\nAccount Number: {account_number}\nName: {first_name} {last_name}\nType: {account_type.capitalize()}"

    except Exception as e:
        return f"Failed to open account: {e}"

# --- DB Connection (Reusable) ---
def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

# --- 1. Open Account Tool ---
@tool
def open_account_form(user_details: dict, account_details: dict) -> str:
    """
    Opens a new user and account together. Provide:
    - user_details: dict with fields from users table
    - account_details: dict with account_type, account_number
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users (first_name, last_name, email, phone, aadhar_number, pan_number,
            date_of_birth, address, city, state, zip_code, country, credit_score)
            VALUES (%(first_name)s, %(last_name)s, %(email)s, %(phone)s, %(aadhar_number)s, %(pan_number)s,
            %(date_of_birth)s, %(address)s, %(city)s, %(state)s, %(zip_code)s, %(country)s, %(credit_score)s)
            RETURNING user_id
        """, user_details)

        user_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO accounts (user_id, account_number, account_type, current_balance, available_balance)
            VALUES (%s, %s, %s, 0.0, 0.0)
        """, (user_id, account_details['account_number'], account_details['account_type']))

        conn.commit()
        return f"Account created successfully for {user_details['first_name']} {user_details['last_name']} with account number {account_details['account_number']}."

    except Exception as e:
        return f"Error creating account: {e}"
    finally:
        if conn:
            cur.close()
            conn.close()

# --- 2. Deposit Money Tool ---
@tool
def deposit_to_account(account_number: str, amount: float) -> str:
    """
    Deposits money to an account and updates balances.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT account_id, current_balance FROM accounts WHERE account_number = %s", (account_number,))
        result = cur.fetchone()
        if not result:
            return "Account not found."

        account_id, current_balance = result
        new_balance = current_balance + amount

        cur.execute("""
            UPDATE accounts SET current_balance = %s, available_balance = %s WHERE account_id = %s
        """, (new_balance, new_balance, account_id))

        cur.execute("""
            INSERT INTO transactions (account_id, transaction_type, amount, running_balance, description, posted_date)
            VALUES (%s, 'deposit', %s, %s, 'Cash deposit', CURRENT_DATE)
        """, (account_id, amount, new_balance))

        conn.commit()
        return f"₹{amount:,.2f} deposited successfully. New balance: ₹{new_balance:,.2f}."

    except Exception as e:
        return f"Error during deposit: {e}"
    finally:
        if conn:
            cur.close()
            conn.close()

# --- 3. Withdraw Money Tool ---
@tool
def withdraw_from_account(account_number: str, amount: float) -> str:
    """
    Withdraws money from account after validating sufficient balance.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT account_id, current_balance FROM accounts WHERE account_number = %s", (account_number,))
        result = cur.fetchone()
        if not result:
            return "Account not found."

        account_id, current_balance = result
        if Decimal(str(amount)) > current_balance:
            return f"Insufficient balance. Available: ₹{current_balance:,.2f}."

        new_balance = current_balance - Decimal(str(amount))
        cur.execute("""
            UPDATE accounts SET current_balance = %s, available_balance = %s WHERE account_id = %s
        """, (new_balance, new_balance, account_id))

        cur.execute("""
            INSERT INTO transactions (account_id, transaction_type, amount, running_balance, description, posted_date)
            VALUES (%s, 'withdrawal', %s, %s, 'ATM withdrawal', CURRENT_DATE)
        """, (account_id, Decimal(str(amount)), new_balance))

        conn.commit()
        return f"₹{amount:,.2f} withdrawn successfully. Remaining balance: ₹{new_balance:,.2f}."

    except Exception as e:
        return f"Error during withdrawal: {e}"
    finally:
        if conn:
            cur.close()
            conn.close()

# --- 4. Transfer Funds Tool ---
@tool
def transfer_funds(from_account: str, to_account: str, amount: float) -> str:
    """
    Transfers funds between accounts. Provide:
    - from_account (str): sender account number
    - to_account (str): receiver account number
    - amount (float): amount to transfer
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Lock sender account and fetch balance
        cur.execute("SELECT current_balance, account_id FROM accounts WHERE account_number = %s FOR UPDATE", (from_account,))
        sender = cur.fetchone()
        if not sender:
            return "Sender account not found."

        sender_balance, sender_id = sender
        if sender_balance < Decimal(str(amount)):
            return f"Insufficient funds. Available balance: ₹{sender_balance:,.2f}"

        # Lock receiver account
        cur.execute("SELECT current_balance, account_id FROM accounts WHERE account_number = %s FOR UPDATE", (to_account,))
        receiver = cur.fetchone()
        if not receiver:
            return "Receiver account not found."

        receiver_balance, receiver_id = receiver

        # Perform the transfer
        new_sender_balance = sender_balance - Decimal(str(amount))
        new_receiver_balance = receiver_balance + Decimal(str(amount))

        # Update sender
        cur.execute("""
            UPDATE accounts SET current_balance = %s, available_balance = %s WHERE account_number = %s
        """, (new_sender_balance, new_sender_balance, from_account))

        # Update receiver
        cur.execute("""
            UPDATE accounts SET current_balance = %s, available_balance = %s WHERE account_number = %s
        """, (new_receiver_balance, new_receiver_balance, to_account))

        # Log sender transaction
        cur.execute("""
            INSERT INTO transactions (account_id, transaction_type, amount, running_balance, description, posted_date)
            VALUES (%s, 'transfer', %s, %s, %s, CURRENT_DATE)
        """, (sender_id, Decimal(str(amount)), new_sender_balance, f'Transfer to {to_account}'))

        # Log receiver transaction
        cur.execute("""
            INSERT INTO transactions (account_id, transaction_type, amount, running_balance, description, posted_date)
            VALUES (%s, 'transfer', %s, %s, %s, CURRENT_DATE)
        """, (receiver_id, Decimal(str(amount)), new_receiver_balance, f'Transfer from {from_account}'))

        conn.commit()
        return f"Successfully transferred ₹{amount:.2f} from {from_account} to {to_account}."

    except Exception as e:
        return f"Transfer failed: {e}"

    finally:
        if conn:
            cur.close()
            conn.close()


# --- 5. Get Transaction History ---
@tool
def get_transaction_history(account_number: str, limit: int = 5) -> str:
    """
    Returns the last N transactions for the given account.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT account_id FROM accounts WHERE account_number = %s", (account_number,))
        row = cur.fetchone()
        if not row:
            return "Account not found."
        account_id = row[0]

        cur.execute("""
            SELECT transaction_date, transaction_type, amount, description, running_balance
            FROM transactions
            WHERE account_id = %s
            ORDER BY transaction_date DESC
            LIMIT %s
        """, (account_id, limit))

        rows = cur.fetchall()
        if not rows:
            return "No transactions found."

        lines = [
            f"{t.strftime('%Y-%m-%d %H:%M')} | {typ} | ₹{amt:,.2f} | {desc} | Balance: ₹{bal:,.2f}"
            for t, typ, amt, desc, bal in rows
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"Error fetching history: {e}"
    finally:
        if conn:
            cur.close()
            conn.close()

# --- 6. Apply for Loan Tool ---
@tool
def apply_for_loan(loan_data: dict) -> str:
    """
    Applies for a loan. Provide all required fields matching the loans table.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO loans (user_id, account_id, loan_type, loan_number, original_amount, current_balance,
                interest_rate, term_months, start_date, maturity_date, payment_frequency,
                next_payment_date, next_payment_amount, status, collateral_description)
            VALUES (%(user_id)s, %(account_id)s, %(loan_type)s, %(loan_number)s, %(original_amount)s,
                %(current_balance)s, %(interest_rate)s, %(term_months)s, %(start_date)s, %(maturity_date)s,
                %(payment_frequency)s, %(next_payment_date)s, %(next_payment_amount)s, %(status)s, %(collateral_description)s)
        """, loan_data)

        conn.commit()
        return "Loan application submitted successfully."
    except Exception as e:
        return f"Error applying for loan: {e}"
    finally:
        if conn:
            cur.close()
            conn.close()

# --- 7. Issue Card Tool ---
@tool
def issue_card(card_data: dict) -> str:
    """
    Issues a new card. Provide all required fields matching the cards table.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO cards (account_id, user_id, card_number, card_type, card_network,
                expiration_date, cvv, issue_date, status, daily_limit, pin_number)
            VALUES (%(account_id)s, %(user_id)s, %(card_number)s, %(card_type)s, %(card_network)s,
                %(expiration_date)s, %(cvv)s, %(issue_date)s, %(status)s, %(daily_limit)s, %(pin_number)s)
        """, card_data)

        conn.commit()
        return "Card issued successfully."
    except Exception as e:
        return f"Error issuing card: {e}"
    finally:
        if conn:
            cur.close()
            conn.close()

# --- 8. Create Fixed Deposit Tool ---
@tool
def create_fixed_deposit(deposit_data: dict) -> str:
    """
    Creates a new fixed deposit. Provide all required fields matching the deposits table.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO deposits (user_id, account_id, deposit_type, deposit_number, amount, interest_rate,
                term_months, start_date, maturity_date, interest_payout, status, auto_renewal, early_withdrawal_penalty)
            VALUES (%(user_id)s, %(account_id)s, %(deposit_type)s, %(deposit_number)s, %(amount)s, %(interest_rate)s,
                %(term_months)s, %(start_date)s, %(maturity_date)s, %(interest_payout)s, %(status)s, %(auto_renewal)s,
                %(early_withdrawal_penalty)s)
        """, deposit_data)

        conn.commit()
        return "Fixed deposit created successfully."
    except Exception as e:
        return f"Error creating fixed deposit: {e}"
    finally:
        if conn:
            cur.close()
            conn.close()

# --- Tool Assembler ---
def get_all_tools(llm, user_id: int | None = None):
    tools = [
        get_retriever_tool(),
        loan_payment_calculator,
        card_bill_calculator,
        get_web_search_tool(),
        compare_loan_emis,
        get_account_balance_by_identity,
        open_account_form,
        deposit_to_account,
        withdraw_from_account,
        transfer_funds,
        get_transaction_history,
        apply_for_loan,
        issue_card,
        create_fixed_deposit,
        
    ]
    if user_id is not None:
        tools.append(get_sql_database_tool(llm, user_id=user_id))
    return tools
