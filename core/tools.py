import os
import numpy_financial as npf
from langchain.tools import tool, Tool
from langchain.tools.retriever import create_retriever_tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from pathlib import Path

# --- Tool 1: Knowledge Base Retriever Tool ---
def get_retriever_tool():
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=os.getenv("GOOGLE_API_KEY"))
    vector_store_path = Path("vectordb/faiss_index")
    vector_store = FAISS.load_local(str(vector_store_path), embeddings, allow_dangerous_deserialization=True)
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    # --- THIS IS THE CRITICAL CHANGE ---
    # The old description was too generic. This one is more explicit.
    retriever_tool = create_retriever_tool(
        retriever,
        "knowledge_base_tool",
        """
        Use this to answer questions about the bank's internal policies, product details, services, FAQs, and procedures.
        This is your primary source for 'how-to' questions like "how to apply for a loan" or questions about
        required documents, account types, interest rates, and specific features of bank products.
        """
    )
    return retriever_tool

# --- Tool 2: Financial Calculator Tool ---
@tool
def loan_payment_calculator(principal: float, annual_rate_percent: float, years: int) -> str:
    """
    Calculates the monthly payment for a loan given the principal, annual interest rate (as a percentage), and loan term in years.
    Use this for any questions about loan payments, mortgages, or amortization.
    """
    try:
        monthly_rate = annual_rate_percent / 12 / 100
        n_payments = years * 12
        monthly_payment = npf.pmt(monthly_rate, n_payments, -principal)
        return f"The estimated monthly payment is ${monthly_payment:,.2f}."
    except Exception as e:
        return f"Error calculating loan payment: {e}"

# --- Tool 3: Web Search Tool ---
def get_web_search_tool():
    web_search_tool = TavilySearchResults(max_results=3)
    # --- THIS IS THE CRITICAL CHANGE ---
    # The old description was too narrow. This one makes it a clear fallback.
    web_search_tool.description = (
        "A web search tool. Use this for general knowledge questions, or when the knowledge_base_tool "
        "does not have the specific information required. It is good for finding information on "
        "financial topics, definitions, or procedures not specific to our bank's internal documents."
    )
    return web_search_tool

# --- Tool 4: SQL Database Tool ---
def get_sql_database_tool(llm):
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    
    db_uri = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    db = SQLDatabase.from_uri(db_uri)

    # Create a separate, specialized agent for SQL tasks
    sql_agent_executor = create_sql_agent(
        llm=llm,
        db=db,
        agent_type="tool-calling",
        verbose=True,
        handle_parsing_errors=True,
    )

    # Wrap the SQL agent executor in a Tool for the main agent to use
    sql_tool = Tool(
        name="customer_database_tool",
        func=sql_agent_executor.invoke,
        description="Use this tool to query the bank's customer database. You can find customer details, account balances, and transaction history. Input should be a full question in natural language about customer data. Example: 'What is the savings account balance for John Doe?'"
    )
    return sql_tool

# --- Function to assemble all tools ---
def get_tools(llm):
    return [
        get_retriever_tool(),
        loan_payment_calculator,
        get_web_search_tool(),
        get_sql_database_tool(llm)
    ]