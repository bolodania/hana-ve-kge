from database import HanaClient
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings, ChatOpenAI
from gen_ai_hub.proxy.gen_ai_hub_proxy import GenAIHubProxyClient
from ai_core_sdk.ai_core_v2_client import AICoreV2Client
from langchain_community.vectorstores.hanavector import HanaDB
from prompts import get_rdf_context, get_sparql_prompt, get_sparql_recovery_prompt, get_final_answer_prompt
from config import load_aicore_config

class HybridRetriever:
    def __init__(self):
        aicore_config = load_aicore_config()

        ai_core_client = AICoreV2Client(
            base_url=aicore_config['AICORE_BASE_URL'],
            auth_url=aicore_config['AICORE_AUTH_URL'],
            client_id=aicore_config['AICORE_CLIENT_ID'],
            client_secret=aicore_config['AICORE_CLIENT_SECRET'],
            resource_group=aicore_config['AICORE_RESOURCE_GROUP']
        )
        
        proxy_client = GenAIHubProxyClient(ai_core_client=ai_core_client)

        self.embedding_model = OpenAIEmbeddings(proxy_model_name='text-embedding-ada-002', proxy_client=proxy_client)
        self.llm = ChatOpenAI(proxy_model_name='gpt-4o', proxy_client=proxy_client)
        self.db = HanaDB(
            embedding=self.embedding_model,
            connection=HanaClient().connection,
            table_name="SUPPLIERS_EMBED_ADA",
            content_column="CONTENT",
            metadata_column="METADATA",
            vector_column="VECTOR"
        )
        self.hana_client = HanaClient()

    def retrieve_vector(self, question, top_k=25):
        retriever = self.db.as_retriever(search_kwargs={'k': top_k})
        return retriever.invoke(question)

    def generate_sparql_query(self, rdf_context, question):
        sparql_llm_chain = get_sparql_prompt() | self.llm
        sparql_query = sparql_llm_chain.invoke({
            "rdf_context": rdf_context,
            "question": question
        })
        return sparql_query.content.strip()

    def regenerate_sparql_with_error_context(self, rdf_context, bad_query, error_message, question):
        print("Regenerating SPARQL due to error:", error_message)

        # Now you feed LLM a **different prompt** saying:
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

    def generate_final_answer(self, vector_context, kg_context, question):
        final_answer_llm_chain = get_final_answer_prompt() | self.llm

        vector_text = "\n\n".join([doc.page_content for doc in vector_context])
        kg_text = "\n".join([str(row) for row in kg_context])

        final_answer = final_answer_llm_chain.invoke({
            "vector_context": vector_text,
            "sparql_context": kg_text,
            "question": question
        })
        return final_answer.content.strip()

    def hybrid_retrieve_and_answer(self, question):
        # Step 1: Vector Search
        vector_context = self.retrieve_vector(question)

        # Step 2: Generate SPARQL
        sparql_query = self.generate_sparql_query(get_rdf_context(), question)

        # Step 3: Execute SPARQL
        kg_context = self.execute_sparql_with_retry(sparql_query, question)

        # Step 4: Final Answer
        return self.generate_final_answer(vector_context, kg_context, question)
