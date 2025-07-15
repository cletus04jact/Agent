import os
import streamlit as st
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

# Initialize embedding model
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

# Load vectorstore
db = FAISS.load_local("vectordb/faiss_index", embeddings, allow_dangerous_deserialization=True)

# Set up retrieval QA chain
retriever = db.as_retriever(search_kwargs={"k": 3})
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=os.getenv("GEMINI_API_KEY")
    ),
    retriever=retriever,
    return_source_documents=True
)

# Streamlit UI
st.set_page_config(page_title="Banking AI Assistant", layout="centered")
st.title("🏦 Banking AI Assistant")
st.markdown("Ask any question related to your bank documents (.pdf, .txt, .json)")

query = st.text_input("🔎 Enter your question here")

if query:
    with st.spinner("Searching..."):
        result = qa_chain(query)
        st.subheader("💬 Answer")
        st.write(result["result"])

        with st.expander("📄 Source Documents"):
            for doc in result["source_documents"]:
                st.markdown(f"**File**: `{doc.metadata.get('source')}`")
                st.markdown(doc.page_content[:500] + "...")
