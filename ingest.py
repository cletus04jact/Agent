import os
import json
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document

load_dotenv()
print("✅ Environment variables loaded successfully.")

def load_custom_json(path):
    documents = []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for item in data:
            question = item.get("question", "")
            answer = item.get("answer", "")
            if question and answer:
                content = f"Q: {question}\nA: {answer}"
                metadata = {"category": item.get("category", "General"), "source": path}
                documents.append(Document(page_content=content, metadata=metadata))
    return documents

def ingest():
    data_dir = "database/general"
    documents = []

    for file in os.listdir(data_dir):
        file_path = os.path.join(data_dir, file)

        if file.endswith(".pdf"):
            try:
                documents.extend(PyPDFLoader(file_path).load())
                print(f"✅ Loaded PDF: {file}")
            except Exception as e:
                print(f"❌ Error loading PDF {file}: {e}")

        elif file.endswith(".json"):
            try:
                documents.extend(load_custom_json(file_path))
                print(f"✅ Loaded JSON: {file}")
            except Exception as e:
                print(f"❌ Error loading JSON {file}: {e}")

    if not documents:
        print("⚠️ No documents found to process.")
        return

    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = splitter.split_documents(documents)

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local("vectordb/faiss_index")
    print("✅ Vectorstore saved successfully with embeddings.")

if __name__ == "__main__":
    ingest()
