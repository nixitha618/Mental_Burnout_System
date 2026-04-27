#!/usr/bin/env python
"""
Fix for ChromaDB SQLite version issue.
Run this before importing chromadb.
"""
import sys
import os

# Override sqlite3 with pysqlite3
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    print("✅ Successfully overridden sqlite3 with pysqlite3")
except ImportError:
    print("⚠️ pysqlite3 not installed. Run: pip install pysqlite3-binary")
