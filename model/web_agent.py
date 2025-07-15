import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools.tavily_search import TavilySearchResults
from .memory import memory

load_dotenv()

def get_web_agent():
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    search_tool = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))

    agent = initialize_agent(
        tools=[search_tool],
        llm=llm,
        agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory,
        verbose=True
    )

    return agent
