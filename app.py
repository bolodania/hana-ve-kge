from retrieval import HybridRetriever

if __name__ == "__main__":
    retriever = HybridRetriever()

    question = "I want to see all suppliers that are facing financial instability and are connected to regions with high geopolitical risks. Specify what issues are observed."
    # question = "What challenges does ProTech face?"
    # question = "Are suppliers in North Korea face issues?"
    
    answer = retriever.hybrid_retrieve_and_answer(question)
    
    print("\n=== Final Answer ===\n")
    print(answer)
