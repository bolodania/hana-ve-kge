from flask import Flask, request, jsonify
import os
from cfenv import AppEnv
from sap import xssec
import functools
from retrieval import HybridRetriever

local_testing = False

app = Flask(__name__)
env = AppEnv()

# Instantiate once, reuse for performance
retriever = HybridRetriever()

port = int(os.environ.get('PORT', 3000))
if not local_testing:
    uaa_service = env.get_service(name='hana-ve-kge_YOUR_NUMBER-uaa').credentials

# Authorization Decorator
def require_auth(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not local_testing:
            if 'authorization' not in request.headers:
                return jsonify({"error": "You are not authorized to access this resource"}), 403
            
            access_token = request.headers.get('authorization')[7:]
            security_context = xssec.create_security_context(access_token, uaa_service)
            is_authorized = security_context.check_scope('uaa.resource')

            if not is_authorized:
                return jsonify({"error": "You are not authorized to access this resource"}), 403

        return f(*args, **kwargs)  # Call the original function if authorized

    return decorated_function


@app.route('/ask', methods=['POST'])
@require_auth
def ask_question():
    data = request.get_json()

    if not data or 'question' not in data:
        return jsonify({'error': 'Please provide a "question" field in the request body.'}), 400

    question = data['question']

    try:
        answer = retriever.hybrid_retrieve_and_answer(question)
        return jsonify({
            "question": question,
            "answer": answer
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
