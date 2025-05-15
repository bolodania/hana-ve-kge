import pandas as pd
import math
import re
from database import HanaClient

# Load data
suppliers = pd.read_csv("sources/suppliers.csv", sep=";")
country_status = pd.read_csv("sources/country_status.csv", sep=";")
country_risk_map = dict(zip(country_status["COUNTRY"], country_status["RISK"]))

# Batch parameters
batch_size = 50
total_suppliers = len(suppliers)
num_batches = math.ceil(total_suppliers / batch_size)

# Function to clean and format URIs
def clean_uri(text):
    """
    Cleans and formats a string to make it URI-friendly.
    - Removes spaces, special characters, and ensures the string is URI-safe.
    """
    text = text.strip()  # Remove spaces at beginning/end
    text = text.replace(" ", "_")  # Replace spaces with underscores
    text = re.sub(r'[^A-Za-z0-9_]', '', text)  # Remove everything except a-z, 0-9, _
    return text

# Initialize HANA client
hana_client = HanaClient()

try:
    for batch_idx in range(num_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, total_suppliers)
        batch = suppliers.iloc[start_idx:end_idx]
        
        # Start building batch SPARQL
        sparql_insert = "PREFIX rag: <http://sap.com/rag/>\n\n"
        sparql_insert += "INSERT DATA {\n"
        sparql_insert += "  GRAPH <rag_suppliers_YOUR_NUMBER> {\n"
        
        for idx, row in batch.iterrows():
            supplier_name = clean_uri(row["SUPPLIER_NAME"])
            supplier_id = row["SUPPLIER_ID"]
            country = clean_uri(row["SUPPLIER_COUNTRY"])
            supplier_type = row["SUPPLIER_TYPE"]
            address = row["SUPPLIER_ADDRESS"]
            city = row["SUPPLIER_CITY"]
            email = row["SUPPLIER_EMAIL"]
            phone = row["SUPPLIER_PHONE"]
            website = row["SUPPLIER_WEBSITE"]

            sparql_insert += f"    rag:{supplier_name} rag:locatedIn rag:{country} .\n"
            sparql_insert += f"    rag:{supplier_name} rag:hasSupplierType \"{supplier_type}\" .\n"
            sparql_insert += f"    rag:{supplier_name} rag:hasSupplierId \"{supplier_id}\" .\n"
            sparql_insert += f'    rag:{supplier_name} rag:hasAddress "{address}" .\n'
            sparql_insert += f'    rag:{supplier_name} rag:locatedInCity "{city}" .\n'
            sparql_insert += f'    rag:{supplier_name} rag:hasEmail "{email}" .\n'
            sparql_insert += f'    rag:{supplier_name} rag:hasPhone "{phone}" .\n'
            sparql_insert += f'    rag:{supplier_name} rag:hasWebsite "{website}" .\n'
            
            if row["SUPPLIER_COUNTRY"] in country_risk_map:
                risk = country_risk_map[row["SUPPLIER_COUNTRY"]]
                sparql_insert += f"    rag:{country} rag:hasGeopoliticalRisk \"{risk}\" .\n"

        # Close SPARQL
        sparql_insert += "  }\n}"
        
        # Execute batch SPARQL
        hana_client.execute_raw_sparql(sparql_insert)
        print(f"Batch {batch_idx+1}/{num_batches} uploaded successfully ✅")

finally:
    # Close the database connection
    hana_client.close()
    print("All batches uploaded! 🚀")