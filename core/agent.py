# core/agent.py

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from .tools import get_tools

# --- THIS IS THE CRITICAL CHANGE ---
# We are giving the agent a new, explicit instruction on how to handle broad queries.
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are Giggso Agent, a friendly and highly capable banking assistant.

        **Your Core Mission:**
        Your main goal is to provide accurate and helpful answers to user questions.

        **Behavioral Rules:**
        1.  **Prioritize Internal Knowledge:** Always try to use the `knowledge_base_tool` first for questions about the bank's products, policies, and procedures.
        2.  **Fallback to Web Search:** If the `knowledge_base_tool` does not provide a sufficient answer, use the `web_search_tool` for general financial information.
        3.  **Proactive Clarification:** If a user's query is broad or ambiguous (e.g., "loans," "account types," "help with cards"), your first step is to use the `knowledge_base_tool`. If that tool returns documents covering several distinct sub-topics, **DO NOT** try to answer directly. Instead, your task is to analyze the retrieved information and present the user with a numbered list of potential follow-up questions to guide them.

        **Example of Proactive Clarification:**
        User: "Tell me about loans."
        Your Ideal Response: "Of course! I found information on several types of loans. To help me narrow it down, which of these are you interested in?
        1. How do I apply for a Personal Loan?
        2. What are the current interest rates for a Home Loan?
        3. What documents are needed for a Car Loan?
        4. Can you tell me about the Education Loan program?"

        **Security Reminder:**
        Never ask for passwords, full account numbers, or other highly sensitive personal information.
        """
    ),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"), # This is where the agent thinks.
])

def create_agent(llm):
    """Creates and returns the main banking agent executor."""
    tools = get_tools(llm)
    
    # The memory object should be part of the agent's state
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    agent = create_tool_calling_agent(llm, tools, prompt)
    
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        memory=memory
    )
    return agent_executor