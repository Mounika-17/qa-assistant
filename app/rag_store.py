import os
from typing import Optional # type hint for values that might be None.

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from sentence_transformers import SentenceTransformer
from langchain.embeddings.base import Embeddings  # For LangChain wrapper

# Loads .env and puts environment variables (like GEMINI_API_KEY) into os.environ for local runs.
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set. Set it in .env or environment variables.")

# Path to knowledge-base folder inside app
# BASE_DIR- directory of current file (app/).It returns the absolute path of the folder where the current Python file(rag_store.py) is located. It returns absolute path to the app folder.
BASE_DIR = os.path.dirname(__file__)
KB_PATH = os.path.join(BASE_DIR, "knowledge_base")


# FAISS_DIR: store the faiss index inside the workspace so it persists within the Space container
# Default: ./qa_faiss_store relative to project root
FAISS_DIR = os.getenv("FAISS_DIR", os.path.join(BASE_DIR, "..", "qa_faiss_store"))
FAISS_DIR = os.path.abspath(FAISS_DIR)

"""
HFEmbeddings is a wrapper class around SentenceTransformer. 

LangChain's FAISS and retriever expect an embedding object that implements two methods:
1. embed_documents(texts) → used when building the FAISS index from documents.
2. embed_query(text) → used when embedding a user query to search against the FAISS index.

The SentenceTransformer library by itself does not know LangChain.
SentenceTransformer provides a single method encode() which can handle one string or a list of strings and convert them into vectors.

Therefore, we create HFEmbeddings to adapt SentenceTransformer to LangChain’s interface.

"""
# Take the HuggingFace embedding model and convert it into a LangChain Embeddings instance
# This class inherits from Embeddings class
class HFEmbeddings(Embeddings):
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    # This method is not aclled directly. FAISS.from_documents internally calls- embeddings.embed_documents([doc.page_content for doc in split_docs]), this is where embed_documents is executed, it takes all PDF chunks convert each chunk to a vector using SentenceTransformer and stores them in FAISS.
    def embed_documents(self, texts):
        return [self.model.encode(t).tolist() for t in texts]
    
    # This method is called when we make a query via a retriever(Ex: retriever.invoke("Your question here")), this method is also not called directly.
    # This method is used when we make a query via the retriever. It converts the query into a vector and returns it so FAISS can search for similar chunks
    def embed_query(self, text):
        return self.model.encode(text).tolist()

# _embeddings can be either a HuggingFace Embeddings instance or None 
_embeddings: Optional[HFEmbeddings] = None
# _vectorstore can be either a FAISS instance or None
_vectorstore: Optional[FAISS] = None

# Method to create and return the GoogleGenerativeAIEmbeddings instance
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HFEmbeddings(
            model_name="all-MiniLM-L6-v2"  # HuggingFace model
        )
    return _embeddings


def build_or_load_vectorstore() -> FAISS:
    """
    Build or load a FAISS vectorstore using PDF files from the knowledge-base.

    Priority:
    1. Reuse in-memory _vectorstore if already loaded.
    2. Load index from disk if FAISS_DIR + index files exist.
    3. Otherwise, build from PDFs under KB_PATH, save, and return.

    Raises:
        FileNotFoundError: If knowledge base directory is missing.
        FileNotFoundError: If knowledge base has no PDF files.
        RuntimeError: If FAISS_DIR is partially corrupted (only one index file).
        ValueError: If PDFs load but produce no text chunks.
    """
    global _vectorstore
    # If _vectorstore is already loaded in memory → reuse it.
    if _vectorstore is not None:
        return _vectorstore
    
    # Get embedding model (needed for langchain to convert queries in to vectors & building index)
    embeddings = get_embeddings()

    # If FAISS index already exists, load it from the disk
    index_file = os.path.join(FAISS_DIR, "index.faiss")
    store_file = os.path.join(FAISS_DIR, "index.pkl")

    faiss_dir_exists = os.path.isdir(FAISS_DIR)
    index_exists = os.path.exists(index_file)
    store_exists = os.path.exists(store_file)

    # Handle corrupted / partial FAISS index case explicitly
    # index_exists != store_exists means This checks if exactly one of the two files exists
    if faiss_dir_exists and (index_exists != store_exists):
        # One file exists but not the other → likely a bad / partial write
        raise RuntimeError(
            f"FAISS index directory '{FAISS_DIR}' appears corrupted: "
            f"index.faiss exists = {index_exists}, index.pkl exists = {store_exists}. "
            "Delete this directory or fix the files before continuing."
        )
     
    # embeddings is passed in the below langchain wrapper, because FAISS only stores the embedding vectors, not the embedding model but our langchain requires the embedding model to convert the query into vector and then compare it with the Faiss index
    # If FAISS index fully exists → load from disk
    if faiss_dir_exists and index_exists and store_exists:
        _vectorstore = FAISS.load_local(
            FAISS_DIR,
            embeddings,
            allow_dangerous_deserialization=True,  # index.pkl is a pickle file and Pickle is not safe for untrusted input. Since you created it, it's safe → so this flag enables loading
        )
        return _vectorstore

    # Otherwise, build from scratch using the PDF docs
    # Check if we have the PDF's present in the knowledge-base
    if not os.path.isdir(KB_PATH):
        raise FileNotFoundError(
            f"Knowledge base directory '{KB_PATH}' not found. "
            "Ensure your PDF files are placed under app/knowledge-base."
        )

    # Load all PDFs in the knowledge-base folder
    loader = DirectoryLoader(
        KB_PATH,
        glob="*.pdf",
        loader_cls=PyPDFLoader,
    )
    docs = loader.load()

    if not docs:
        # No PDFs or no readable content
        raise FileNotFoundError(
            f"No PDF files found in knowledge base directory '{KB_PATH}'. "
            "Add at least one .pdf file to build the vectorstore."
        )
    
    # Split PDFs in to smaller chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", "!", "?", ",", " "],
    )
  
    split_docs = splitter.split_documents(docs)

    if not split_docs:
        # PDFs loaded but chunking produced nothing (rare, but safe to handle)
        raise ValueError(
            "PDFs were loaded but no text chunks were produced after splitting. "
            "Check if the PDFs contain extractable text."
        )
    
    # Create FAISS index 
    _vectorstore = FAISS.from_documents(
        split_docs,
        embeddings,
    )

    # Save FAISS index to disk, Create a FAISS_DIR if it not exists and save the content in it.
    os.makedirs(FAISS_DIR, exist_ok=True)
    # Under FAISS_DIR, it will create index.pkl and index.faiss.
    # index.faiss contains All knowledge encoded as vectors + the search structure needed to quickly find similar chunks
    # index.pkl contains The text + metadata + mapping — everything needed to reconstruct documents.
    _vectorstore.save_local(FAISS_DIR)

    return _vectorstore


def get_retriever():
    """
    Return a retriever object that can be used to search the knowledge base.
    """
    vectorstore = build_or_load_vectorstore()
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}, # Return 4 most similar chunks
    )
    return retriever
