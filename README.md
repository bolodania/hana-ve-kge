# Supplier Knowledge Graph Explorer

This repository contains a Python-based service designed to retrieve and analyze supplier information using a hybrid approach of vector search and SPARQL queries. The service is structured for deployment on the SAP BTP Cloud Foundry environment.

## Features

- **Hybrid Retrieval**: Combines vector-based search with SPARQL queries to retrieve supplier information from unstructured and structured data.
- **Knowledge Graph Integration**: Leverages RDF-based knowledge graphs to provide insights into supplier relationships and geopolitical risks.
- **AI-Powered Query Generation**: Utilizes AI models to generate SPARQL queries and refine them in case of errors.
- **Web API**: Exposes a REST API for querying supplier information.
- **Deployment Ready**: Includes scripts and configuration files for streamlined deployment on SAP BTP Cloud Foundry.

## Repository Structure

- **Application Code**:
  - `api.py`: Flask-based web server exposing the `/ask` endpoint for querying supplier information.
  - `app.py`: CLI-based entry point for testing the hybrid retrieval process.
  - `retrieval.py`: Implements the hybrid retrieval logic combining vector search and SPARQL queries.
  - `prompts.py`: Defines prompt templates for AI-powered SPARQL query generation and refinement.
  - `database.py`: Handles interactions with the SAP HANA database.
  - `config.py`: Loads configuration for SAP HANA and AI Core.

- **Configuration**:
  - `manifest.yml`: Configuration file for deploying the application on SAP BTP Cloud Foundry.
  - `xs-security.json`: Security configuration for SAP BTP Cloud Foundry.
  - `config/env_cloud.json`: Contains SAP HANA connection details.
  - `config/env_config.json`: Contains SAP AI Core connection details.

- **Data Sources**:
  - `sources/suppliers.csv`: Supplier data with details like name, country, and contact information.
  - `sources/country_status.csv`: Geopolitical risk levels for various countries.

- **Deployment**:
  - `deploy.sh`: Shell script to automate the deployment process.
  - `Procfile`: Specifies the command to run the application on platforms like Heroku.

- **Miscellaneous**:
  - `.gitignore`: Specifies files and directories to be ignored by Git.
  - `requirements.txt`: Lists the Python dependencies required to run the application.
  - `runtime.txt`: Specifies the Python runtime version.

## Deployment

### Prerequisites

1. Install the [Cloud Foundry CLI](https://docs.cloudfoundry.org/cf-cli/install-go-cli.html).
2. Ensure you have access to an SAP BTP Cloud Foundry environment.
<!-- 3. TODO: add info about HANA and AI Core -->

### Steps

1. Create the `config/env_cloud.json` file with the following content:
   ```json
   {
       "url": "<HANA_URL>",
       "port": "<HANA_PORT>",
       "user": "<HANA_USER>",
       "pwd": "<HANA_PASSWORD>"
   }
   ```

2. Create the `config/env_config.json` file with the following content:
   ```json
   {
       "AICORE_AUTH_URL": "<AICORE_AUTH_URL>",
       "AICORE_CLIENT_ID": "<AICORE_CLIENT_ID>",
       "AICORE_CLIENT_SECRET": "<AICORE_CLIENT_SECRET>",
       "AICORE_BASE_URL": "<AICORE_BASE_URL>",
       "AICORE_RESOURCE_GROUP": "<AICORE_RESOURCE_GROUP>"
   }
   ```

3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Deploy the application:
   ```bash
   bash deploy.sh
   ```

## Usage

### Web API

Once deployed, the service exposes a REST API at the `/ask` endpoint. You can send a POST request with a JSON payload containing the `question` field.

Example request:
```bash
curl -X POST http://<your-app-url>/ask \
-H "Content-Type: application/json" \
-d '{"question": "Which suppliers are located in high-risk countries?"}'
```

Example response:
```json
{
    "question": "Which suppliers are located in high-risk countries?",
    "answer": "StandSolutions (Russia) and VisionCam_UA (Ukraine) are located in high-risk countries."
}
```

### CLI

You can also test the hybrid retrieval process locally using the `app.py` script:
```bash
python3 app.py
```

In case you want to test the server side locally, make sure that `local_testing` variable is set to `True` and run:
```bash
python3 api.py
```

## Dependencies

- Python (version specified in `runtime.txt`)
- Required Python packages listed in `requirements.txt`

## Configuration

- Review and modify the configuration files (`manifest.yml`, `xs-security.json`, `config/env_cloud.json`, `config/env_config.json`) to align with your deployment environment and security requirements.

## Known Limitations

- The service relies on accurate and complete data in the knowledge graph and vector database.
- Error handling for SPARQL query execution is limited to a single retry.

# Supplier Knowledge Graph Explorer Jupyter Notebook

For an interactive, step-by-step guide to using the hybrid retrieval process, refer to the Jupyter Notebook:

- [Hybrid Retrieval Workshop Notebook](hybrid_retrieval_workshop.ipynb)

This notebook demonstrates how to:
- Perform vector search to retrieve unstructured data.
- Dynamically generate SPARQL queries using a Language Model (LLM).
- Execute SPARQL queries to retrieve structured data from the knowledge graph.
- Combine results from vector search and SPARQL to generate meaningful answers.

## How to Use the Notebook
1. Ensure all prerequisites mentioned in the notebook are met.
2. Open the notebook in Jupyter Notebook or JupyterLab.
3. Follow the steps outlined in the notebook to explore the hybrid retrieval process interactively.

<!-- 
## Contributing

Feel free to open issues or submit pull requests to improve the project.

## License

This project is licensed under the MIT License. See the LICENSE file for details. -->