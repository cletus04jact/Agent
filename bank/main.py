import streamlit as st
from services.account_info import verify_user_and_get_balance

st.title("Bank Account Balance Checker")

st.write("Please enter your registered details:")

account_number = st.text_input("Account Number")
aadhar = st.text_input("Aadhar Number")

if st.button("Check Balance"):
    if not account_number or not aadhar:
        st.warning("Please enter both account_number and Aadhar Number.")
    else:
        try:
            results = verify_user_and_get_balance(account_number, aadhar)
            if results:
                for record in results:
                    st.success(f"""
                        Hello {record[3]} {record[4]},
                        Account Number: {record[0]}
                        Type: {record[1]}
                        Current Balance: ₹{record[2]:,.2f}
                    """)
            else:
                st.error("No account found. Please check your details.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
