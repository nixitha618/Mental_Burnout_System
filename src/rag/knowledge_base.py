"""
Knowledge Base module for RAG pipeline with SQLite fix
This module handles vector database operations for wellness guidance retrieval.
"""

# ===== CRITICAL FIX FOR CHROMADB SQLITE VERSION =====
import sys
import os
import subprocess

try:
    import pysqlite3
    sys.modules['sqlite3'] = pysqlite3
    print("✅ SQLite override successful")
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pysqlite3-binary"])
    import pysqlite3
    sys.modules['sqlite3'] = pysqlite3
    print("✅ SQLite override successful after installation")
# ====================================================

import sqlite3
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import warnings
warnings.filterwarnings("ignore")

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config.settings import VECTOR_DB_DIR
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SimpleEmbedder:
    """Simple TF-IDF based embedder - no external dependencies"""
    
    def __init__(self, dim=384):
        self.dim = dim
        self.vectorizer = TfidfVectorizer(
            max_features=dim,
            stop_words='english',
            lowercase=True
        )
        self.is_fitted = False
    
    def encode(self, texts, show_progress_bar=False):
        """Convert texts to embeddings"""
        if isinstance(texts, str):
            texts = [texts]
        
        if not self.is_fitted:
            embeddings = self.vectorizer.fit_transform(texts).toarray()
            self.is_fitted = True
        else:
            embeddings = self.vectorizer.transform(texts).toarray()
        
        if embeddings.shape[1] < self.dim:
            pad_width = ((0, 0), (0, self.dim - embeddings.shape[1]))
            embeddings = np.pad(embeddings, pad_width, mode='constant')
        elif embeddings.shape[1] > self.dim:
            embeddings = embeddings[:, :self.dim]
        
        return embeddings.tolist()


class KnowledgeBase:
    def __init__(self, collection_name="wellness_guidance"):
        self.collection_name = collection_name
        self.vector_db_dir = VECTOR_DB_DIR
        self.embedder = SimpleEmbedder()
        
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.vector_db_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
            logger.info(f"✅ Loaded existing collection with {self.collection.count()} documents")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"✅ Created new collection: {collection_name}")
    
    def add_documents(self, documents, metadatas=None, ids=None):
        if not documents:
            return
        
        logger.info(f"Generating embeddings for {len(documents)} documents...")
        embeddings = self.embedder.encode(documents)
        
        if ids is None:
            ids = [f"doc_{i:06d}" for i in range(len(documents))]
        
        if metadatas is None:
            metadatas = [{} for _ in range(len(documents))]
        
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            end = min(i + batch_size, len(documents))
            self.collection.add(
                documents=documents[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end],
                ids=ids[i:end]
            )
        
        logger.info(f"✅ Added {len(documents)} documents to knowledge base")
    
    def search(self, query, n_results=5):
        query_embedding = self.embedder.encode([query])
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, self.collection.count()),
            include=["documents", "metadatas", "distances"]
        )
        
        return results
    
    def get_stats(self):
        return {
            'name': self.collection_name,
            'document_count': self.collection.count(),
            'path': str(self.vector_db_dir),
            'sqlite_version': sqlite3.sqlite_version
        }


_kb = None

def get_knowledge_base():
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


if __name__ == "__main__":
    print("="*50)
    print("Testing Knowledge Base")
    print("="*50)
    kb = get_knowledge_base()
    print(f"✅ Knowledge Base ready: {kb.get_stats()}")