import pandas as pd
import math

# Load data
suppliers = pd.read_csv("sources/suppliers.csv", sep=";")
country_status = pd.read_csv("sources/country_status.csv", sep=";")
country_risk_map = dict(zip(country_status["COUNTRY"], country_status["RISK"]))

# Batch parameters
batch_size = 50
total_suppliers = len(suppliers)
num_batches = math.ceil(total_suppliers / batch_size)

# Connect to HANA
from hdbcli import dbapi
import json
import os

with open(os.path.join(os.getcwd(), 'env_cloud.json')) as f:
    hana_env_c = json.load(f)

HANA_SCHEMA = "RAG"

connDBAPI = dbapi.connect(
            address=hana_env_c['url'],
            port=hana_env_c['port'],
            user=hana_env_c['user'],
            password=hana_env_c['pwd'],
            currentSchema= HANA_SCHEMA
        )
cursor = connDBAPI.cursor()

import re

# Function to clean and format URIs
# This function will remove spaces, special characters, and make the string URI-friendly
# It will also ensure that the string is lowercase and does not start with a number
def clean_uri(text):
    # text = text.lower()  # make lowercase
    text = text.strip()  # remove spaces at beginning/end
    text = text.replace(" ", "_")  # replace spaces with underscore
    text = re.sub(r'[^A-Za-z0-9_]', '', text)  # remove everything except a-z, 0-9, _
    return text


for batch_idx in range(num_batches):
    start_idx = batch_idx * batch_size
    end_idx = min(start_idx + batch_size, total_suppliers)
    batch = suppliers.iloc[start_idx:end_idx]
    
    # Start building batch SPARQL
    sparql_insert = "PREFIX rag: <http://sap.com/rag/>\n\n"
    sparql_insert += "INSERT DATA {\n"
    sparql_insert += "  GRAPH <rag_suppliers> {\n"
    
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
    
    # Execute batch
    cursor.callproc('SPARQL_EXECUTE', (sparql_insert, '', '', None))
    print(f"Batch {batch_idx+1}/{num_batches} uploaded successfully ✅")

# Close connection
connDBAPI.close()
print("All batches uploaded! 🚀")
