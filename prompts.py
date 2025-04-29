from langchain.prompts import PromptTemplate

# Define the context about the RDF schema
def get_rdf_context():
    return """
            Your RDF graph uses the following structure:

            Namespaces:
            - rag: <http://sap.com/rag/>

            Supplier entities (identified by SUPPLIER_NAME) have the following properties:
            - rag:locatedIn → the supplier's country (IRI reference).
            - rag:hasSupplierType → type of supplier (Literal: "Manufacturer" or "Reseller").
            - rag:hasSupplierId → supplier ID (Literal string).
            - rag:hasAddress → supplier address (Literal string).
            - rag:locatedInCity → supplier city (Literal string).
            - rag:hasEmail → supplier email (Literal string).
            - rag:hasPhone → supplier phone (Literal string).
            - rag:hasWebsite → supplier website (Literal string).

            Country entities (identified by SUPPLIER_COUNTRY) have the following properties:
            - rag:hasGeopoliticalRisk → geopolitical risk level (Literal string: "High", "Medium", "Low").

            Example triples:
            - rag:StandSolutions rag:locatedIn rag:Russia .
            - rag:StandSolutions rag:hasSupplierType "Manufacturer" .
            - rag:StandSolutions rag:hasAddress "Tverskaya St 7, Moscow, Russia" .
            - rag:Russia rag:hasGeopoliticalRisk "High" .

            """

def get_sparql_prompt():

    sparql_prompt_template = """
        Generate a SPARQL query for the user question.

        Given the following RDF context: {rdf_context}
        
        And the user question:
        '{question}'

        Instructions:
        - Query the GRAPH <rag_suppliers>.
        - Always use the 'rag:' prefix for entities and predicates.
        - Available query variables include: ?supplierName, ?supplierType, ?supplierId, ?address, ?city, ?email, ?phone, ?website, ?country, ?risk.
        - You must only use available variables. Do NOT use any incorrect or undefined variables.
        - Every variable you SELECT must be BOUND (linked to an entity or literal) inside WHERE.
        - If you need to access values like geopolitical risk ("High", "Low"), you must bind it first:
            Example: ?country rag:hasGeopoliticalRisk ?risk .
        - Apply FILTERS *after* binding the variable.
        - DO NOT directly compare inside triple patterns like ?country rag:hasGeopoliticalRisk "High" if you SELECT ?risk.
        - When using IRIs for suppliers or countries, replace spaces with underscores (e.g., 'North Korea' → North_Korea). Do not remove spaces entirely.
        - Return ONLY the SPARQL query body (SELECT ... FROM ... WHERE ...).
        - Do NOT wrap it with CALL SPARQL_EXECUTE.
        - Format it as SPARQL query (NO code blocks like ```sparql or ```).

        Add the prefix declaration at the start of the query, like:
        PREFIX rag: <http://sap.com/rag/>

        Example:
        PREFIX rag: <http://sap.com/rag/>
        SELECT ?supplier ?supplierType ?country ?risk
        FROM <rag_suppliers>
        WHERE {{
            ?supplier rag:locatedIn ?country .
            ?supplier rag:hasSupplierType ?supplierType .
            ?country rag:hasGeopoliticalRisk ?risk .
            FILTER(?risk = "High")
        }}
        
        """

    return PromptTemplate(
        template=sparql_prompt_template,
        input_variables=["rdf_context","question"]
    )

def get_sparql_recovery_prompt():

    recovery_prompt_template = """
        Given the RDF context: {rdf_context}

        And the user question:
        '{question}'

        A SPARQL query was generated, but it caused an execution error.

        Problematic query:
        {bad_query}

        Error Message:
        {error_message}

        Instructions:
        - Generate a SPARQL query for the user question.
        - Query the GRAPH <rag_suppliers>.
        - Always use the 'rag:' prefix for entities and predicates.
        - Available query variables include: ?supplierName, ?supplierType, ?supplierId, ?address, ?city, ?email, ?phone, ?website, ?country, ?risk.
        - You must only use available variables. Do NOT use any incorrect or undefined variables.
        - Every variable you SELECT must be BOUND (linked to an entity or literal) inside WHERE.
        - If you need to access values like geopolitical risk ("High", "Low"), you must bind it first:
            Example: ?country rag:hasGeopoliticalRisk ?risk .
        - Apply FILTERS *after* binding the variable.
        - DO NOT directly compare inside triple patterns like ?country rag:hasGeopoliticalRisk "High" if you SELECT ?risk.
        - When using IRIs for suppliers or countries, replace spaces with underscores (e.g., 'North Korea' → North_Korea). Do not remove spaces entirely.
        - Return ONLY the SPARQL query body (SELECT ... FROM ... WHERE ...).
        - Do NOT wrap it with CALL SPARQL_EXECUTE.
        - Format it as SPARQL query (NO code blocks like ```sparql or ```).

        Add the prefix declaration at the start of the query, like:
        PREFIX rag: <http://sap.com/rag/>

        Example:
        PREFIX rag: <http://sap.com/rag/>
        SELECT ?supplier ?supplierType ?country ?risk
        FROM <rag_suppliers>
        WHERE {{
            ?supplier rag:locatedIn ?country .
            ?supplier rag:hasSupplierType ?supplierType .
            ?country rag:hasGeopoliticalRisk ?risk .
            FILTER(?risk = "High")
        }}
    
        """

    return PromptTemplate(
        template=recovery_prompt_template,
        input_variables=["rdf_context", "bad_query", "error_message", "original_user_question"]
    )

def get_final_answer_prompt():
    return PromptTemplate(
        input_variables=["vector_context", "sparql_context", "question"],
        template="""
            Context:
            You are tasked with helping retrieve and summarize supplier information.

            Available information:
            - Unstructured document chunks ({vector_context}).
            - Structured knowledge graph results ({sparql_context}).

            User Question:
            {question}

            Instructions:
            - Only suppliers that appear in the knowledge graph may be included in the final answer.
            - Use unstructured document data *only* to enrich or clarify facts about suppliers already found in the knowledge graph.
            - Do not include any supplier names, risk classifications, or attributes that are mentioned *only* in unstructured data.
            - If a supplier appears in documents but is not present in the knowledge graph, exclude it from the answer and state: "Information not available."
            - Do not infer or assume facts — all conclusions must be backed by knowledge graph validation.
            - Optionally, include supporting information from unstructured data *if* it aligns with the knowledge graph result.
            - Prefer clarity and structured presentation (use lists or bullets). Optionally, return structured JSON if many suppliers are involved.

            Return:
            - A clean, human-readable summary limited to validated suppliers only.
            - Ensure all risk indicators are grounded in validated graph entries.

            """
    )
