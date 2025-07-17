import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from pathlib import Path
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Get the base directory of the script
base_dir = Path(__file__).resolve().parent
# Define the path to the FAISS index
index_path = base_dir.parent / "vectordb" / "faiss_index"

# --- Load API Key with Verification ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found. Please check your .env file.")

print("Successfully loaded GOOGLE_API_KEY.") # For debugging

# ---  Load FAISS Vector Store ---
print("Loading embeddings and vector store...")
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=api_key
)
vector_store = FAISS.load_local(
    str(index_path),
    embeddings,
    allow_dangerous_deserialization=True
)
print("Vector store loaded.")

# --- Setup Memory ---
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# ---  Load Gemini LLM ---
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.5,
    google_api_key=api_key
)

# --- Create the Conversational Chain ---
qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=vector_store.as_retriever(),
    memory=memory,
    verbose=True
)

# --- Run the Model (CLI Interface) ---
def run_agent():
    print("\n🔎 Ask a general banking question (type 'exit' to quit):")
    while True:
        query = input("You: ")
        if query.lower() == "exit":
            break
        # The .run method is simpler for single input/output, but .invoke is the newer standard
        response = qa_chain.invoke({"question": query})
        print("AI:", response['answer'])

if __name__ == "__main__":
    run_agent()