import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from core.agent import create_agent

# Load environment variables from .env file at the start
load_dotenv()

def main():
    """Main function to initialize and run the banking agent."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found. Please check your .env file.")

    # Initialize the primary LLM for the agent
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.3,
        google_api_key=api_key
    )

    # Create the agent executor
    agent_executor = create_agent(llm)

    print("🤖 Giggso Banking Agent is online. How can I help you today? (type 'exit' to quit)")
    
    while True:
        try:
            query = input("You: ")
            if query.lower() == "exit":
                print("👋 Goodbye!")
                break
            
            response = agent_executor.invoke({"input": query})
            print("AI:", response['output'])

        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()