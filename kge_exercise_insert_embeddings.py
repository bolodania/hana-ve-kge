from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_hana import HanaDB
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings
from gen_ai_hub.proxy.gen_ai_hub_proxy import GenAIHubProxyClient
from ai_core_sdk.ai_core_v2_client import AICoreV2Client
from database import HanaClient
from config import load_aicore_config
import time

# Start timer
start_time = time.time()

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

# Extract chunks from the PDF
chunks = extract_chunks_from_pdf_with_langchain("sources/Supplier_Performance_Report_Detailed.pdf")

# Load configurations
aicore_config = load_aicore_config()

# Initialize HANA client
hana_client = HanaClient()

# Initialize AICore client and proxy
ai_core_client = AICoreV2Client(
    base_url=aicore_config['AICORE_BASE_URL'],
    auth_url=aicore_config['AICORE_AUTH_URL'],
    client_id=aicore_config['AICORE_CLIENT_ID'],
    client_secret=aicore_config['AICORE_CLIENT_SECRET'],
    resource_group=aicore_config['AICORE_RESOURCE_GROUP']
)

# Initialize GenAIHub proxy client
proxy_client = GenAIHubProxyClient(ai_core_client=ai_core_client)

# Initialize embedding model and LLM
embedding_model = OpenAIEmbeddings(proxy_model_name='text-embedding-ada-002', proxy_client=proxy_client)

# Define HANA table and schema
HANA_TABLE = "SUPPLIERS_EMBED_ADA_YOUR_NUMBER"

# Create a LangChain VectorStore interface for the HANA database
db = HanaDB(
    connection=hana_client.connection,
    embedding=embedding_model,
    table_name=HANA_TABLE,
    content_column="CONTENT",
    metadata_column="METADATA",
    vector_column="VECTOR"
)

# Delete already existing documents from the table
db.delete(filter={})

# Add the loaded document chunks
db.add_documents(chunks)

# Commit and close the database connection
hana_client.connection.commit()
hana_client.close()

# End the timer
end_time = time.time()

# Print execution time
execution_time = end_time - start_time
print(f"Table {HANA_TABLE} has been created successfully. Execution time: {execution_time:.4f} seconds")