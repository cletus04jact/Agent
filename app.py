# app.py

import streamlit as st
import os
import random
import psycopg2
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from core.agent import create_agent_executor
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from auth.users import authenticate_user, verify_otp_and_create_session
from core.agent import create_agent_executor
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import uuid

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user_sessions = {}

llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3, google_api_key=os.getenv("GOOGLE_API_KEY"))

class LoginRequest(BaseModel):
    user_id: int
    password: str

class OTPRequest(BaseModel):
    user_id: int
    otp: str

class ChatInput(BaseModel):
    session_id: str
    message: str
    chat_history: list[str] = []

@app.post("/login")
async def login(data: LoginRequest):
    if not authenticate_user(data.user_id, data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    from auth.otp import send_otp
    send_otp(data.user_id)
    return {"message": "OTP sent"}

@app.post("/verify-otp")
async def verify_otp(data: OTPRequest):
    user_id = verify_otp_and_create_session(data.user_id, data.otp)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    session_id = str(uuid.uuid4())
    user_sessions[session_id] = user_id
    return {"session_id": session_id}

@app.post("/chat")
async def chat(data: ChatInput):
    user_id = user_sessions.get(data.session_id)
    if not user_id:
        raise HTTPException(status_code=403, detail="Please login to access account-specific data")

    agent_executor = create_agent_executor(llm, user_id=user_id)
    response = await agent_executor.ainvoke({
        "input": data.message,
        "chat_history": data.chat_history,
    })
    return {"reply": response["output"]}

# --- AGENT & LLM SETUP ---
@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3, google_api_key=os.getenv("GOOGLE_API_KEY"))

# This function is now very lightweight
def get_agent_executor(user_id=None):
    llm = get_llm()
    return create_agent_executor(llm, user_id=user_id)

# --- MAIN STREAMLIT APP ---
def main():
    load_dotenv()
    st.set_page_config(page_title="Giggso Banking Agent", page_icon="🤖", layout="wide")

    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "initial_choice"
        st.session_state.messages = []
        st.session_state.user_id = None

    # ... (initial_choice and login UI logic is unchanged) ...
    if st.session_state.app_mode == "initial_choice":
        st.title("Welcome to the Giggso Banking Assistant")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Log In for Personalized Service", use_container_width=True):
                st.session_state.app_mode = "login"
                st.rerun()
        with col2:
            if st.button("Continue with General Queries", use_container_width=True):
                st.session_state.app_mode = "guest_chat"
                st.session_state.messages = [AIMessage(content="You are in Guest Mode. How can I help you with general banking questions?")]
                st.rerun()

    elif st.session_state.app_mode == "login":
        st.title("Login with Mobile and Aadhar")

        mobile = st.text_input("Enter your registered mobile number")
        aadhar = st.text_input("Enter your Aadhar number")

        if st.button("Verify and Login"):
            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT")
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, first_name, last_name
                FROM users
                WHERE phone = %s AND aadhar_number = %s AND is_active = TRUE
            """, (mobile, aadhar))
            result = cursor.fetchone()
            conn.close()

            if result:
                user_id, first_name, last_name = result
                st.session_state.app_mode = "logged_in_chat"
                st.session_state.user_id = user_id
                st.session_state.user_name = f"{first_name} {last_name}"
                st.session_state.messages = [
                    AIMessage(content=f"Welcome, {st.session_state.user_name}! How can I assist you with your account today?")
                ]
                st.rerun()
            else:
                st.error("Invalid mobile or Aadhar number.")


    # --- Main Chat Interface ---
    elif st.session_state.app_mode in ["guest_chat", "logged_in_chat"]:
        is_logged_in = st.session_state.app_mode == "logged_in_chat"
        title = "Personalized Banking Assistant" if is_logged_in else "General Banking Assistant"
        caption = f"Logged in as {st.session_state.get('user_name', '')}" if is_logged_in else "Guest Mode"
        
        st.title(title)
        st.caption(caption)

        for message in st.session_state.messages:
            with st.chat_message(message.type):
                st.write(message.content)

        if prompt := st.chat_input("Ask me anything..."):
            st.session_state.messages.append(HumanMessage(content=prompt))
            with st.chat_message("human"):
                st.write(prompt)

            with st.chat_message("ai"):
                with st.spinner("Thinking..."):
                    agent_executor = get_agent_executor(user_id=st.session_state.user_id)
                    
                    # THE CRITICAL INVOCATION: We pass the entire history from our session state.
                    # The agent is now stateless and relies completely on this history for context.
                    response = agent_executor.invoke({
                        "input": prompt,
                        "chat_history": st.session_state.messages[:-1] # History up to the current turn
                    })
                    
                    st.write(response["output"])
                    st.session_state.messages.append(AIMessage(content=response["output"]))

if __name__ == "__main__":
    main()