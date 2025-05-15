from hdbcli import dbapi
from config import load_hana_config

hana_env = load_hana_config()

class HanaClient:
    def __init__(self):
        self.connection = dbapi.connect(
            address=hana_env['url'],
            port=hana_env['port'],
            user=hana_env['user'],
            password=hana_env['pwd']
        )
        self.cursor = self.connection.cursor()

    def execute_raw_sparql(self, sparql_query):

        print("Generated SPARQL Query:\n", sparql_query)  # optional debug

        try:
            resp = self.cursor.callproc('SPARQL_EXECUTE', (
                sparql_query,
                'Accept: application/sparql-results+csv',
                '?',
                None
            ))
            metadata = resp[3]
            results = resp[2]
            
            # Print results
            print("Query Response:", results)
            print("Response Metadata:", metadata)

            return results, metadata
        except Exception as e:
            raise RuntimeError(f"SPARQL_EXECUTE failed: {e}")

    def close(self):
        if self.connection:
            self.connection.close()
