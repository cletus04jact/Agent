import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from pathlib import Path

load_dotenv()

# --- CONFIGURATION ---
SOURCE_DOCS_DIR = Path("source_documents")
VECTOR_STORE_DIR = Path("vectordb/faiss_index")

def load_documents():
    """Loads all PDF and JSON documents from the source directory."""
    documents = []
    # Load PDFs
    for doc_path in SOURCE_DOCS_DIR.glob("*.pdf"):
        loader = PyPDFLoader(str(doc_path))
        documents.extend(loader.load())
        print(f"Loaded {doc_path.name}")
        
    # Load JSON files with the corrected schema
    for doc_path in SOURCE_DOCS_DIR.glob("*.json"):
        print(f"Loading JSON file: {doc_path.name}")
        loader = JSONLoader(
            file_path=str(doc_path),
            # This schema iterates through each object in the root array '[ ]'
            # and formats the question and answer into a single text document.
            jq_schema='.[] | "Question: " + .question + "\nAnswer: " + .answer',
            text_content=True, # We are creating the text content directly with jq
        )
        try:
            documents.extend(loader.load())
            print(f"Successfully loaded and processed {doc_path.name}")
        except Exception as e:
            print(f"Error loading {doc_path.name}. Check if it's a valid JSON array. Error: {e}")

    return documents

def main():
    print("--- Starting Data Ingestion ---")
    
    # 1. Load documents
    docs = load_documents()
    if not docs:
        print("No documents found in the 'source_documents' directory. Exiting.")
        return

    # 2. Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    splits = text_splitter.split_documents(docs)
    print(f"Split {len(docs)} documents into {len(splits)} chunks.")

    # 3. Create embeddings
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found. Please check your .env file.")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)

    # 4. Create and save FAISS vector store
    print(f"Creating vector store from {len(splits)} document chunks...")
    vector_store = FAISS.from_documents(splits, embeddings)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(VECTOR_STORE_DIR))
    
    print("--- Data Ingestion Complete ---")
    print(f"Vector store saved at: {VECTOR_STORE_DIR}")

if __name__ == "__main__":
    main()