#!/usr/bin/env python3
"""Initialize the Suntory database with required tables"""

import sqlite3
from pathlib import Path

def init_database():
    """Create all required database tables"""
    db_path = Path('/Users/cjq/Dev/MyProjects/AutoGen/v3/data/suntory.db')
    db_path.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            model TEXT,
            mode TEXT
        )
    """)

    # Create messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)

    # Create user_preferences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preference_key TEXT UNIQUE NOT NULL,
            preference_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for better performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_conversation
        ON messages(conversation_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp
        ON messages(timestamp)
    """)

    conn.commit()
    conn.close()

    print("✓ Database initialized successfully")
    print("  - conversations table created")
    print("  - messages table created")
    print("  - user_preferences table created")
    print("  - indexes created")

if __name__ == "__main__":
    init_database()