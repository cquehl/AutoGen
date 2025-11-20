"""
Suntory v3 - Persistence Layer
SQLite for session history, ChromaDB for agent memory
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings
from .telemetry import get_logger

logger = get_logger(__name__)

Base = declarative_base()


# =============================================================================
# SQLAlchemy Models
# =============================================================================

class ConversationHistory(Base):
    """Conversation history table"""
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    extra_data = Column(Text, nullable=True)  # JSON metadata (renamed from 'metadata' which is reserved)


class AgentAction(Base):
    """Agent action log"""
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    agent_name = Column(String(100), nullable=False)
    action_type = Column(String(100), nullable=False)  # tool_call, delegation, completion
    action_data = Column(Text, nullable=False)  # JSON data
    result = Column(Text, nullable=True)  # JSON result


class SessionMetadata(Base):
    """Session metadata"""
    __tablename__ = "session_metadata"

    session_id = Column(String(100), primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    user_name = Column(String(100), nullable=True)
    extra_data = Column(Text, nullable=True)  # JSON metadata (renamed from 'metadata' which is reserved)


# =============================================================================
# Database Manager
# =============================================================================

class DatabaseManager:
    """Manages SQLite database for session history"""

    def __init__(self, database_url: Optional[str] = None):
        settings = get_settings()
        self.database_url = database_url or settings.database_url

        # Convert SQLite URL for async usage
        if self.database_url.startswith("sqlite:///"):
            async_url = self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        else:
            async_url = self.database_url

        self.engine = create_async_engine(async_url, echo=False)
        self.async_session_maker = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        logger.info("Database manager initialized", database_url=self.database_url)

    async def initialize(self):
        """Create all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async def add_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add conversation entry"""
        async with self.async_session_maker() as session:
            entry = ConversationHistory(
                session_id=session_id,
                correlation_id=correlation_id,
                role=role,
                content=content,
                extra_data=json.dumps(metadata) if metadata else None
            )
            session.add(entry)
            await session.commit()

    async def add_agent_action(
        self,
        session_id: str,
        agent_name: str,
        action_type: str,
        action_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ):
        """Add agent action log"""
        async with self.async_session_maker() as session:
            action = AgentAction(
                session_id=session_id,
                correlation_id=correlation_id,
                agent_name=agent_name,
                action_type=action_type,
                action_data=json.dumps(action_data),
                result=json.dumps(result) if result else None
            )
            session.add(action)
            await session.commit()

    async def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        # For simplicity, using synchronous query
        # In production, use async queries properly
        from sqlalchemy import select

        async with self.async_session_maker() as session:
            query = select(ConversationHistory).where(
                ConversationHistory.session_id == session_id
            ).order_by(ConversationHistory.timestamp.desc())

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            entries = result.scalars().all()

            return [
                {
                    "id": entry.id,
                    "role": entry.role,
                    "content": entry.content,
                    "timestamp": entry.timestamp.isoformat(),
                    "metadata": json.loads(entry.extra_data) if entry.extra_data else None
                }
                for entry in reversed(entries)  # Return in chronological order
            ]


# =============================================================================
# Vector Store Manager (ChromaDB)
# =============================================================================

class VectorStoreManager:
    """Manages ChromaDB for agent memory and RAG"""

    def __init__(self, persist_directory: Optional[str] = None):
        settings = get_settings()
        self.persist_directory = persist_directory or str(settings.get_chroma_path())

        # Ensure directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        logger.info(
            "Vector store manager initialized",
            persist_directory=self.persist_directory
        )

    def get_or_create_collection(self, name: str):
        """Get or create a collection"""
        return self.client.get_or_create_collection(
            name=name,
            metadata={"description": f"Agent memory collection: {name}"}
        )

    def add_memory(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ):
        """Add documents to agent memory"""
        collection = self.get_or_create_collection(collection_name)

        # Generate IDs if not provided
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]

        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(
            "Added memories to collection",
            collection=collection_name,
            count=len(documents)
        )

    def query_memory(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5
    ) -> Dict[str, Any]:
        """Query agent memory"""
        collection = self.get_or_create_collection(collection_name)

        results = collection.query(
            query_texts=query_texts,
            n_results=n_results
        )

        logger.info(
            "Queried collection",
            collection=collection_name,
            n_results=n_results
        )

        return results

    def clear_collection(self, collection_name: str):
        """Clear a collection"""
        try:
            self.client.delete_collection(name=collection_name)
            logger.info("Cleared collection", collection=collection_name)
        except Exception as e:
            logger.warning(f"Failed to clear collection: {e}")


# =============================================================================
# Singletons
# =============================================================================

_db_manager: Optional[DatabaseManager] = None
_vector_manager: Optional[VectorStoreManager] = None


async def get_db_manager() -> DatabaseManager:
    """Get or create database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    return _db_manager


def get_vector_manager() -> VectorStoreManager:
    """Get or create vector store manager singleton"""
    global _vector_manager
    if _vector_manager is None:
        _vector_manager = VectorStoreManager()
    return _vector_manager


def reset_persistence():
    """Reset persistence managers (useful for testing)"""
    global _db_manager, _vector_manager
    _db_manager = None
    _vector_manager = None
