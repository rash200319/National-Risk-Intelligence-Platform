import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
import hashlib
import os
from pathlib import Path

from config import DB_PATH

DB_NAME = DB_PATH

# Ensure database directory exists
db_parent = Path(DB_NAME).parent
db_parent.mkdir(parents=True, exist_ok=True)

class DatabaseManager:
    def __init__(self, db_path: str = DB_NAME):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self._init_tables()
    
    def _get_connection(self):
        """Create a database connection with WAL mode enabled."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        # ENABLE WAL MODE (Write-Ahead Logging) -> Allows reading while writing
        conn.execute("PRAGMA journal_mode=WAL;") 
        return conn
    
    def _init_tables(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            c = conn.cursor()
            
            # Risks table with enhanced schema for historical data
            c.execute('''
                CREATE TABLE IF NOT EXISTS risks (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    link TEXT,
                    published TEXT,
                    risk_score INTEGER,
                    category TEXT,
                    location TEXT,
                    district TEXT,
                    province TEXT,
                    confidence FLOAT DEFAULT 1.0,
                    keywords TEXT,
                    sentiment_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_historical BOOLEAN DEFAULT 0,
                    data_source TEXT,
                    raw_data TEXT
                )
            ''')
            
            # Historical data collection status
            c.execute('''
                CREATE TABLE IF NOT EXISTS historical_collection (
                    source TEXT PRIMARY KEY,
                    last_collected_date TEXT,
                    status TEXT,
                    total_collected INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Location reference data for Sri Lanka
            c.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    parent_id INTEGER,
                    geo_json TEXT,
                    population INTEGER,
                    risk_profile TEXT,
                    FOREIGN KEY (parent_id) REFERENCES locations (id)
                )
            ''')
            
            # Time series data for trend analysis
            c.execute('''
                CREATE TABLE IF NOT EXISTS risk_trends (
                    date TEXT,
                    location_id INTEGER,
                    category TEXT,
                    avg_risk_score FLOAT,
                    event_count INTEGER,
                    PRIMARY KEY (date, location_id, category),
                    FOREIGN KEY (location_id) REFERENCES locations (id)
                )
            ''')
            
            # Create a table for tracking data collection
            c.execute('''
                CREATE TABLE IF NOT EXISTS data_collection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    items_collected INTEGER DEFAULT 0,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add indexes for better query performance
            c.execute('CREATE INDEX IF NOT EXISTS idx_risks_source ON risks(source)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risks_risk_score ON risks(risk_score)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risks_created_at ON risks(created_at)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_risks_published ON risks(published)')
            
            conn.commit()

    def _generate_id(self, source: str, signal: str) -> str:
        """Generate a unique ID for a record."""
        unique_str = f"{source}_{signal}"
        return hashlib.md5(unique_str.encode('utf-8')).hexdigest()
    
    def insert_risk(self, record: Dict[str, Any]) -> bool:
        """Insert a single risk record (Safe against duplicates)."""
        return self.batch_insert_risks([record]) > 0

    def batch_insert_risks(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert multiple risk records safely.
        Uses INSERT OR IGNORE logic based on the Deterministic ID.
        """
        if not records:
            return 0
            
        inserted_count = 0
        
        with self._get_connection() as conn:
            c = conn.cursor()
            
            for record in records:
                # 1. Generate Deterministic ID (Source + Signal)
                # This ensures if we fetch the same news twice, we get the same ID.
                if 'id' not in record or record['id'].startswith(('news_', 'reddit_')):
                    # If ID is missing or random (from uuid), overwrite it with hash
                    record['id'] = self._generate_id(record.get('source', ''), record.get('signal', ''))

                # 2. Ensure all fields exist
                keys = [
                    'id', 'source', 'signal', 'link', 'published', 'risk_score',
                    'category', 'location', 'district', 'province', 
                    'confidence', 'keywords', 'sentiment_score', 'created_at'
                ]
                
                # Fill missing keys with defaults
                clean_record = {k: record.get(k, None) for k in keys}
                if clean_record['created_at'] is None:
                    clean_record['created_at'] = datetime.now().isoformat()

                # 3. Insert or Ignore
                try:
                    c.execute("""
                        INSERT OR IGNORE INTO risks (
                            id, source, signal, link, published, risk_score,
                            category, location, district, province,
                            confidence, keywords, sentiment_score, created_at
                        ) VALUES (
                            :id, :source, :signal, :link, :published, :risk_score,
                            :category, :location, :district, :province,
                            :confidence, :keywords, :sentiment_score, :created_at
                        )
                    """, clean_record)
                    
                    if c.rowcount > 0:
                        inserted_count += 1
                        
                except sqlite3.Error as e:
                    print(f"Database Error on record {clean_record['id']}: {e}")
            
            conn.commit()
            
        return inserted_count

    def get_risks(
        self,
        limit: int = 100,
        offset: int = 0,
        min_score: Optional[int] = None,
        sources: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Query risks with filtering options."""
        query = """
            SELECT * FROM risks
            WHERE 1=1
        """
        params = {}
        
        if min_score is not None:
            query += " AND risk_score >= :min_score"
            params['min_score'] = min_score
            
        if sources:
            placeholders = []
            for idx, source in enumerate(sources):
                key = f"source_{idx}"
                placeholders.append(f":{key}")
                params[key] = source
            query += f" AND source IN ({', '.join(placeholders)})"

        if start_date:
            query += " AND published >= :start_date"
            params['start_date'] = start_date

        if end_date:
            query += " AND published <= :end_date"
            params['end_date'] = end_date

        query += " ORDER BY COALESCE(published, created_at) DESC LIMIT :limit OFFSET :offset"
        params['limit'] = max(1, int(limit))
        params['offset'] = max(0, int(offset))
        
        try:
            with self._get_connection() as conn:
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            print(f"Error fetching risks: {e}")
            return pd.DataFrame()
    
    def get_risk_stats(self) -> Dict[str, Any]:
        """Get statistics about risks in the database."""
        with self._get_connection() as conn:
            # Total count
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as total FROM risks")
            total = c.fetchone()['total']
            
            # Count by source
            c.execute("""
                SELECT source, COUNT(*) as count 
                FROM risks 
                GROUP BY source 
                ORDER BY count DESC
            """)
            sources = [dict(row) for row in c.fetchall()]
            
            return {
                'total_risks': total,
                'sources': sources
            }

# Create a singleton instance
db = DatabaseManager()

# Backward compatibility functions
def init_db():
    pass 

def save_risks(df):
    if df.empty:
        return 0
    records = df.to_dict('records')
    return db.batch_insert_risks(records)