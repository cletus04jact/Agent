import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from .memory import memory

load_dotenv()

def get_local_qa():
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    vectorstore = FAISS.load_local("vectordb/faiss_index", embeddings, allow_dangerous_deserialization=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True
    )

    return qa_chain
