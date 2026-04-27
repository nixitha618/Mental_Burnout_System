"""
Retriever module for RAG pipeline - fetches relevant documents from knowledge base
"""

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.rag.knowledge_base import get_knowledge_base
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Retriever:
    def __init__(self):
        self.kb = get_knowledge_base()
    
    def retrieve(self, query: str, n_results: int = 3, filter_by_risk: str = None) -> List[Dict]:
        """Retrieve relevant documents based on query"""
        logger.info(f"Retrieving documents for: {query}")
        
        results = self.kb.search(query, n_results=n_results * 2)
        
        if not results or not results['documents']:
            logger.warning("No results found")
            return []
        
        formatted_results = []
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            if filter_by_risk and metadata.get('risk_level'):
                if metadata['risk_level'].lower() != filter_by_risk.lower():
                    continue
            
            formatted_results.append({
                'content': doc,
                'metadata': metadata,
                'relevance_score': 1 - distance,
                'id': results['ids'][0][i]
            })
        
        formatted_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        logger.info(f"Retrieved {len(formatted_results[:n_results])} relevant documents")
        return formatted_results[:n_results]
    
    def retrieve_by_topic(self, topic: str, n_results: int = 3) -> List[Dict]:
        """Retrieve documents by specific topic"""
        topics = {
            'stress': 'stress management relaxation anxiety coping techniques',
            'sleep': 'sleep hygiene insomnia rest bedtime routine quality',
            'workload': 'work life balance productivity time management boundaries',
            'exercise': 'physical activity fitness exercise movement wellness',
            'nutrition': 'diet nutrition healthy eating meals hydration',
            'social': 'social connection relationships community support isolation',
            'mindfulness': 'meditation mindfulness awareness breathing presence'
        }
        
        enhanced_query = topics.get(topic.lower(), topic)
        return self.retrieve(enhanced_query, n_results)
    
    def retrieve_by_risk_factors(self, risk_factors: List[str], n_results: int = 3) -> List[Dict]:
        """Retrieve documents based on specific risk factors"""
        if not risk_factors:
            return []
        
        query = " ".join([f"how to improve {factor}" for factor in risk_factors])
        return self.retrieve(query, n_results)


if __name__ == "__main__":
    print("Testing Retriever...")
    retriever = Retriever()
    results = retriever.retrieve("stress management", n_results=2)
    print(f"Found {len(results)} results")