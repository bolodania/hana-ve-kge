from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import CharacterTextSplitter
import time

start_time = time.time()  # Start timer

def extract_chunks_from_pdf_with_langchain(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50):
    """
    Extracts text chunks from a PDF file using LangChain, preserving metadata like page number.
    
    Args:
        file_path (str): Path to the PDF file.
        chunk_size (int): Maximum size of each text chunk.
        chunk_overlap (int): Overlap size between chunks.
        
    Returns:
        List[Document]: List of LangChain Document objects with text and metadata.
    """
    # Step 1: Load the PDF using PyMuPDFLoader
    loader = PyMuPDFLoader(file_path)
    pages = loader.load()  # List of Documents, each corresponding to a page

    # Step 2: Initialize a text splitter
    text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Step 3: Split the documents into smaller chunks while preserving metadata
    chunks = text_splitter.split_documents(pages)

    return chunks

chunks = extract_chunks_from_pdf_with_langchain("sources/Supplier_Performance_Report_Detailed.pdf")
# for chunk in chunks:
#     print(chunk.metadata)
#     print(chunk.page_content)

#Set up HANA Cloud Connection
from hdbcli import dbapi
import json
import os
from dotenv import load_dotenv
# Import the embeddings module from SAPs Generative AI Hub SDK
from gen_ai_hub.proxy.langchain import OpenAIEmbeddings

load_dotenv()

with open(os.path.join(os.getcwd(), 'env_cloud.json')) as f:
    hana_env_c = json.load(f)

with open(os.path.join(os.getcwd(), 'env_config.json')) as f:
    aicore_config = json.load(f)

HANA_SCHEMA = "RAG"
HANA_TABLE = "SUPPLIERS_EMBED_ADA"

connDBAPI = dbapi.connect(
            address=hana_env_c['url'],
            port=hana_env_c['port'],
            user=hana_env_c['user'],
            password=hana_env_c['pwd'],
            currentSchema= HANA_SCHEMA
        )

#Initiate the embedding model to be used from GenAI Hub and provide additional parameters as chunk size
embeddings = OpenAIEmbeddings(proxy_model_name='text-embedding-ada-002', chunk_size=100, max_retries=10)

# Open dbapi connection
cursor = connDBAPI.cursor()

from langchain_community.vectorstores.hanavector import HanaDB
#Create a LangChain VectorStore interface for the HANA database and specify the table (collection) to use for accessing the vector embeddings

db = HanaDB(
    connection=connDBAPI,
    embedding=embeddings,
    table_name=HANA_TABLE,
    content_column="CONTENT",
    metadata_column="METADATA",
    vector_column="VECTOR"
)

# Delete already existing documents from the table
db.delete(filter={})

# add the loaded document chunks
db.add_documents(chunks)

# Commit and Close Connection
connDBAPI.commit()
cursor.close()
connDBAPI.close()

# End the timer
end_time = time.time()

# Print execution time
execution_time = end_time - start_time
print(f"Table {HANA_TABLE} has been created successfully. Execution time: {execution_time:.4f} seconds")