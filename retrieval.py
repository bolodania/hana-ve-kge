from database import HanaClient
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings, ChatOpenAI
from gen_ai_hub.proxy.gen_ai_hub_proxy import GenAIHubProxyClient
from ai_core_sdk.ai_core_v2_client import AICoreV2Client
from langchain_hana import HanaDB
from prompts import get_rdf_context, get_sparql_prompt, get_sparql_recovery_prompt, get_final_answer_prompt
from config import load_aicore_config
import csv
from io import StringIO

class HybridRetriever:
    def __init__(self):
        # Load AICore configuration
        aicore_config = load_aicore_config()
        
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
        self.embedding_model = OpenAIEmbeddings(proxy_model_name='text-embedding-ada-002', proxy_client=proxy_client)
        self.llm = ChatOpenAI(proxy_model_name='gpt-4o', proxy_client=proxy_client)
        
        # Initialize HanaDB
        self.db = HanaDB(
            embedding=self.embedding_model,
            connection=HanaClient().connection,
            table_name="SUPPLIERS_EMBED_ADA_YOUR_NUMBER",
            content_column="CONTENT",
            metadata_column="METADATA",
            vector_column="VECTOR"
        )
        self.hana_client = HanaClient()

        # Initialize pseudonymization mappings
        self.pseudonymization_map = {
            "supplierName": {},
            "supplierId": {},
            "address": {},
            "email": {},
            "phone": {},
            "website": {}
        }
        self.pseudonymization_counter = 1

    def retrieve_vector(self, question, top_k=25):
        """
        Retrieve the top_k most relevant documents from the vector database.
        """
        retriever = self.db.as_retriever(search_kwargs={'k': top_k})
        return retriever.invoke(question)

    def generate_sparql_query(self, rdf_context, question):
        """
        Generates a SPARQL query based on the RDF context and user question.
        """
        sparql_llm_chain = get_sparql_prompt() | self.llm
        sparql_query = sparql_llm_chain.invoke({
            "rdf_context": rdf_context,
            "question": question
        })
        return sparql_query.content.strip()

    def regenerate_sparql_with_error_context(self, rdf_context, bad_query, error_message, question):
        """
        Regenerates the SPARQL query using the error context.
        """
        print("Regenerating SPARQL due to error:", error_message)

        # Now we feed LLM a **different prompt** saying:
        # "This query caused an error, please regenerate it properly."

        recovery_chain = get_sparql_recovery_prompt() | self.llm

        recovery_output = recovery_chain.invoke({
            "rdf_context": rdf_context,
            "bad_query": bad_query,
            "error_message": error_message,
            "question": question
        })


        return recovery_output.content.strip()
    
    def execute_sparql_with_retry(self, sparql_query, question, max_retries=1):
        """
        Executes the SPARQL query and retries if an error occurs.
        """
        try:
            return self.hana_client.execute_raw_sparql(sparql_query)[0]  # only return result
        except Exception as e:
            print(f"SPARQL error: {e}")
            if max_retries > 0:
                regenerated_query = self.regenerate_sparql_with_error_context(
                    self.rdf_context, sparql_query, str(e), question
                )
                return self.execute_sparql_with_retry(regenerated_query, question, max_retries - 1)
            else:
                print("SPARQL regeneration failed.")
                return None
            
    def pseudonymize_value(self, field, value):
        """
        Pseudonymizes a value for a specific field and stores the mapping.
        """
        if value not in self.pseudonymization_map[field]:
            placeholder = f"MASKED_{field.upper()}_{self.pseudonymization_counter}"
            self.pseudonymization_map[field][value] = placeholder
            self.pseudonymization_counter += 1
        return self.pseudonymization_map[field][value]

    def pseudonymize_kg_context(self, kg_context_csv):
        """
        Pseudonymizes sensitive fields in the kg_context CSV data.
        """
        pseudonymized_rows = []
        csv_reader = csv.DictReader(StringIO(kg_context_csv))
        
        for row in csv_reader:
            # Pseudonymize sensitive fields
            row["supplierName"] = self.pseudonymize_value("supplierName", row["supplierName"])
            row["supplierId"] = self.pseudonymize_value("supplierId", row["supplierId"])
            row["address"] = self.pseudonymize_value("address", row["address"])
            row["email"] = self.pseudonymize_value("email", row["email"])
            row["phone"] = self.pseudonymize_value("phone", row["phone"])
            row["website"] = self.pseudonymize_value("website", row["website"])
            pseudonymized_rows.append(row)
        
        # Convert back to CSV format
        output = StringIO()
        csv_writer = csv.DictWriter(output, fieldnames=csv_reader.fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(pseudonymized_rows)
        
        return output.getvalue()

    def generate_final_answer(self, vector_context, kg_context, question):
        """
        Generates the final answer by combining vector and KG context.
        """
        final_answer_llm_chain = get_final_answer_prompt() | self.llm

        vector_text = "\n\n".join([doc.page_content for doc in vector_context])
        # kg_text = "\n".join([str(row) for row in kg_context])
        kg_text = self.pseudonymize_kg_context(kg_context)
        print("KG Text:", kg_text)

        final_answer = final_answer_llm_chain.invoke({
            "vector_context": vector_text,
            "sparql_context": kg_text,
            "question": question
        })
        return final_answer.content.strip()
    
    def restore_original_values_in_response(self, response_text):
        """
        Restores original values in the LLM response by replacing pseudonymized placeholders
        with their corresponding original values, and removes the 'http://sap.com/rag/' namespace.
        """
        for field, mapping in self.pseudonymization_map.items():
            for original, pseudonymized in mapping.items():
                # Remove the namespace from the original value
                clean_original = original.replace("http://sap.com/rag/", "")
                # Replace pseudonymized placeholders with the cleaned original values
                response_text = response_text.replace(pseudonymized, clean_original)
        return response_text

    def hybrid_retrieve_and_answer(self, question):
        """
        Main function to retrieve information and generate an answer.
        """

        # Step 1: Vector Search
        vector_context = self.retrieve_vector(question)

        # Step 2: Generate SPARQL
        sparql_query = self.generate_sparql_query(get_rdf_context(), question)

        # Step 3: Execute SPARQL
        kg_context = self.execute_sparql_with_retry(sparql_query, question)

        # Step 4: Final Answer
        pseudonymized_answer = self.generate_final_answer(vector_context, kg_context, question)

        # Step 5: Restore Original Values in the Response
        restored_answer = self.restore_original_values_in_response(pseudonymized_answer)
        
        self.hana_client.close()

        return restored_answer
