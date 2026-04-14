"""
Memory Persistence Module for RAG System
Implements session state persistence for conversation history, user context, and RAG state.
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class Message:
    """Represents a chat message in conversation history."""
    role: str
    content: str
    timestamp: str
    message_id: str = field(default_factory=lambda: str(time.time()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=data['timestamp'],
            message_id=data.get('message_id', str(time.time()))
        )


@dataclass
class UserContext:
    """Represents user context and preferences."""
    user_id: str
    preferences: Dict[str, Any]
    last_session: str
    conversation_count: int = 0
    session_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user context to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserContext':
        """Create user context from dictionary."""
        return cls(
            user_id=data['user_id'],
            preferences=data.get('preferences', {}),
            last_session=data['last_session'],
            conversation_count=data.get('conversation_count', 0),
            session_metadata=data.get('session_metadata', {})
        )


class MemoryPersistence:
    """
    Memory persistence manager for RAG system.
    Supports both file-based and in-memory storage.
    """
    
    def __init__(
        self,
        storage_path: str = None,
        use_memory_fallback: bool = False,
        auto_save: bool = True
    ):
        """
        Initialize memory persistence.
        
        Args:
            storage_path: Path to persistence file (JSON format)
            use_memory_fallback: Use in-memory storage instead of file
            auto_save: Automatically save changes
        """
        self.storage_path = storage_path or "./ai_workspace/memory/persistence.json"
        self.use_memory_fallback = use_memory_fallback
        self.auto_save = auto_save
        self.memory_cache: Dict[str, Any] = {}
        self._memory_cache_loaded_from_disk: bool = False
        self._ensure_storage_directory()
        
        # Load existing data if file exists
        if not self.use_memory_fallback and os.path.exists(self.storage_path):
            self._load_from_file()
        elif self.use_memory_fallback and self.auto_save and os.path.exists(self.storage_path):
            # Pre-load memory cache from disk when using memory fallback with auto_save
            self._load_memory_cache_from_disk()
    
    def _ensure_storage_directory(self) -> None:
        """Ensure storage directory exists."""
        storage_dir = os.path.dirname(self.storage_path)
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)
    
    def _load_from_file(self) -> None:
        """Load data from persistence file."""
        try:
            with open(self.storage_path, 'r') as f:
                self.memory_cache = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load persistence file: {e}")
            self.memory_cache = {}
    
    def _write_to_file(self, key: str, data: Dict[str, Any]) -> None:
        """Write data to persistent storage."""
        if self.use_memory_fallback:
            self.memory_cache[key] = data
            return
        
        # Ensure directory exists
        self._ensure_storage_directory()
        
        # Load existing data
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    storage = json.load(f)
            except (json.JSONDecodeError, IOError):
                storage = {}
        else:
            storage = {}
        
        # Update and save
        storage[key] = data
        with open(self.storage_path, 'w') as f:
            json.dump(storage, f, indent=2, default=str)
    
    def _write_to_file_disk_only(self, key: str, data: Dict[str, Any]) -> None:
        """Write data to disk without using memory cache (used when use_memory_fallback=True)."""
        # Ensure directory exists
        self._ensure_storage_directory()
        
        # Load existing data
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    storage = json.load(f)
            except (json.JSONDecodeError, IOError):
                storage = {}
        else:
            storage = {}
        
        # Update and save
        storage[key] = data
        with open(self.storage_path, 'w') as f:
            json.dump(storage, f, indent=2, default=str)
    
    def _read_from_file(self, key: str, subkey: str = None) -> Optional[Dict[str, Any]]:
        """Read data from persistent storage."""
        if self.use_memory_fallback:
            # When auto_save=True, load from disk into memory cache on first access
            if self.auto_save and not self._memory_cache_loaded_from_disk:
                self._load_memory_cache_from_disk()
            return self.memory_cache.get(key, {})
        
        if not os.path.exists(self.storage_path):
            return None
        
        try:
            with open(self.storage_path, 'r') as f:
                storage = json.load(f)
            data = storage.get(key, {})
            
            # If subkey is provided, return nested data
            if subkey and isinstance(data, dict) and subkey in data:
                return data[subkey]
            
            return data
        except (json.JSONDecodeError, IOError):
            return None
    
    def _load_memory_cache_from_disk(self) -> None:
        """Load memory cache from disk (used when use_memory_fallback=True with auto_save=True)."""
        if not os.path.exists(self.storage_path):
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                self.memory_cache = json.load(f)
            self._memory_cache_loaded_from_disk = True
        except (json.JSONDecodeError, IOError):
            self.memory_cache = {}
            self._memory_cache_loaded_from_disk = True
    
    def save_conversation(self, messages: List[Message], session_id: str) -> bool:
        """
        Save conversation history to persistent storage.
        
        Args:
            messages: List of messages to save
            session_id: Session identifier
            
        Returns:
            True if save was successful
        """
        start_time = time.time()
        
        data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "messages": [m.to_dict() for m in messages]
        }
        
        self._write_to_file(f"conversation_{session_id}", data)
        
        elapsed = time.time() - start_time
        print(f"Conversation saved in {elapsed:.3f}s")
        
        return elapsed < 1.0  # Performance check
    
    def load_conversation(self, session_id: str) -> List[Message]:
        """
        Load conversation history from persistent storage.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of messages in the conversation
        """
        data = self._read_from_file(f"conversation_{session_id}")
        
        if not data or "messages" not in data:
            return []
        
        return [Message.from_dict(m) for m in data["messages"]]
    
    def save_user_context(self, context: UserContext) -> bool:
        """
        Save user context to persistent storage.
        
        Args:
            context: User context to save
            
        Returns:
            True if save was successful
        """
        start_time = time.time()
        
        self._write_to_file(f"user_context_{context.user_id}", context.to_dict())
        
        elapsed = time.time() - start_time
        print(f"User context saved in {elapsed:.3f}s")
        
        return elapsed < 1.0  # Performance check
    
    def load_user_context(self, user_id: str) -> Optional[UserContext]:
        """
        Load user context from persistent storage.
        
        Args:
            user_id: User identifier
            
        Returns:
            User context if found, None otherwise
        """
        data = self._read_from_file(f"user_context_{user_id}")
        
        if not data:
            return None
        
        return UserContext.from_dict(data)
    
    def save_rag_state(self, state: Dict[str, Any], state_name: str = "default") -> bool:
        """
        Save RAG index state to persistent storage.
        
        Args:
            state: RAG state dictionary to save
            state_name: Name identifier for the state
            
        Returns:
            True if save was successful
        """
        start_time = time.time()
        
        self._write_to_file(f"rag_state_{state_name}", state)
        
        elapsed = time.time() - start_time
        print(f"RAG state saved in {elapsed:.3f}s")
        
        return elapsed < 1.0  # Performance check
    
    def load_rag_state(self, state_name: str = "default") -> Optional[Dict[str, Any]]:
        """
        Load RAG index state from persistent storage.
        
        Args:
            state_name: Name identifier for the state
            
        Returns:
            RAG state dictionary if found, None otherwise
        """
        return self._read_from_file(f"rag_state_{state_name}")
    
    def save_session_state(self, session_id: str, state: Dict[str, Any]) -> bool:
        """
        Save complete session state including conversation and context.
        
        Args:
            session_id: Session identifier
            state: Complete session state dictionary
            
        Returns:
            True if save was successful
        """
        start_time = time.time()
        
        state["session_id"] = session_id
        state["timestamp"] = datetime.now().isoformat()
        
        self._write_to_file(f"session_{session_id}", state)
        
        elapsed = time.time() - start_time
        print(f"Session state saved in {elapsed:.3f}s")
        
        return elapsed < 1.0
    
    def load_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load complete session state from persistent storage.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Complete session state dictionary if found, None otherwise
        """
        return self._read_from_file(f"session_{session_id}")
    
    def list_sessions(self) -> List[str]:
        """
        List all saved session IDs.
        
        Returns:
            List of session IDs
        """
        if self.use_memory_fallback:
            return [
                k.replace("conversation_", "").replace("session_", "")
                for k in self.memory_cache.keys()
                if k.startswith("conversation_") or k.startswith("session_")
            ]
        
        sessions = []
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    storage = json.load(f)
                
                for key in storage.keys():
                    if key.startswith("conversation_"):
                        sessions.append(key.replace("conversation_", ""))
                    elif key.startswith("session_"):
                        sessions.append(key.replace("session_", ""))
            except (json.JSONDecodeError, IOError):
                pass
        
        return list(set(sessions))
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear all data for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if clear was successful
        """
        if self.use_memory_fallback:
            keys_to_remove = [
                k for k in self.memory_cache.keys()
                if k.startswith(f"conversation_{session_id}") or
                   k.startswith(f"session_{session_id}")
            ]
            for key in keys_to_remove:
                del self.memory_cache[key]
            return True
        
        # For file-based, we'll just reload to clear cache
        self._load_from_file()
        return True
    
    def clear_all(self) -> bool:
        """
        Clear all persisted data.
        
        Returns:
            True if clear was successful
        """
        self.memory_cache = {}
        
        if not self.use_memory_fallback and os.path.exists(self.storage_path):
            try:
                os.remove(self.storage_path)
            except OSError:
                return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get persistence statistics.
        
        Returns:
            Dictionary with persistence statistics
        """
        stats = {
            "storage_path": self.storage_path,
            "use_memory_fallback": self.use_memory_fallback,
            "auto_save": self.auto_save,
            "cache_size": len(self.memory_cache),
            "sessions_count": len(self.list_sessions())
        }
        
        if not self.use_memory_fallback and os.path.exists(self.storage_path):
            stats["file_size"] = os.path.getsize(self.storage_path)
        
        return stats
