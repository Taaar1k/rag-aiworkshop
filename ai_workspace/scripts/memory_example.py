#!/usr/bin/env python3
"""
Memory Persistence Example for RAG System
Demonstrates session state persistence across restarts.

Usage:
    python memory_example.py [--memory-fallback] [--storage-path PATH]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.memory_persistence import (
    MemoryPersistence,
    Message,
    UserContext
)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}\n")


def example_basic_usage() -> None:
    """Basic usage example."""
    print_section("Example 1: Basic Usage")
    
    # Initialize persistence
    persistence = MemoryPersistence(
        storage_path="./ai_workspace/memory/persistence_example.json",
        use_memory_fallback=False
    )
    
    print(f"Storage path: {persistence.storage_path}")
    print(f"Using memory fallback: {persistence.use_memory_fallback}")
    
    # Save conversation
    messages = [
        Message(role="user", content="What is RAG?", timestamp=datetime.now().isoformat()),
        Message(role="assistant", content="RAG is Retrieval-Augmented Generation", timestamp=datetime.now().isoformat()),
        Message(role="user", content="How does it work?", timestamp=datetime.now().isoformat())
    ]
    
    persistence.save_conversation(messages, "example_session_1")
    print("✓ Conversation saved")
    
    # Load conversation
    loaded = persistence.load_conversation("example_session_1")
    print(f"✓ Loaded {len(loaded)} messages")
    
    for msg in loaded:
        print(f"  - {msg.role}: {msg.content}")


def example_user_context() -> None:
    """User context persistence example."""
    print_section("Example 2: User Context Persistence")
    
    persistence = MemoryPersistence(
        storage_path="./ai_workspace/memory/persistence_example.json",
        use_memory_fallback=False
    )
    
    # Save user context
    context = UserContext(
        user_id="user_123",
        preferences={
            "theme": "dark",
            "language": "en",
            "notifications": True
        },
        last_session=datetime.now().isoformat(),
        conversation_count=5,
        session_metadata={"ip": "192.168.1.1", "device": "desktop"}
    )
    
    persistence.save_user_context(context)
    print("✓ User context saved")
    
    # Load user context
    loaded = persistence.load_user_context("user_123")
    if loaded:
        print(f"✓ Loaded user: {loaded.user_id}")
        print(f"  Preferences: {json.dumps(loaded.preferences, indent=2)}")
        print(f"  Conversation count: {loaded.conversation_count}")


def example_rag_state() -> None:
    """RAG state persistence example."""
    print_section("Example 3: RAG State Persistence")
    
    persistence = MemoryPersistence(
        storage_path="./ai_workspace/memory/persistence_example.json",
        use_memory_fallback=False
    )
    
    # Simulate RAG state
    rag_state = {
        "vector_store": {
            "collection_name": "documents",
            "embedding_model": "all-MiniLM-L6-v2",
            "document_count": 1000
        },
        "graph_index": {
            "nodes": 500,
            "edges": 1500,
            "entity_types": ["person", "organization", "location"]
        },
        "last_updated": datetime.now().isoformat()
    }
    
    persistence.save_rag_state(rag_state, "default")
    print("✓ RAG state saved")
    
    # Load RAG state
    loaded = persistence.load_rag_state("default")
    if loaded:
        print(f"✓ Loaded RAG state")
        print(f"  Vector store: {loaded['vector_store']['document_count']} documents")
        print(f"  Graph index: {loaded['graph_index']['nodes']} nodes")


def example_session_continuity() -> None:
    """Complete session continuity example."""
    print_section("Example 4: Complete Session Continuity")
    
    persistence = MemoryPersistence(
        storage_path="./ai_workspace/memory/persistence_example.json",
        use_memory_fallback=False
    )
    
    # Simulate first session
    print("Session 1:")
    messages1 = [
        Message(role="user", content="I want to analyze sales data", timestamp=datetime.now().isoformat()),
        Message(role="assistant", content="I can help with that. What time period?", timestamp=datetime.now().isoformat()),
    ]
    
    context1 = UserContext(
        user_id="analyst_001",
        preferences={"theme": "dark"},
        last_session=datetime.now().isoformat(),
        conversation_count=1
    )
    
    persistence.save_conversation(messages1, "session_001")
    persistence.save_user_context(context1)
    print("  ✓ Saved session 1")
    
    # Simulate second session (after restart)
    print("\nSession 2 (after restart):")
    
    # Load previous context
    loaded_context = persistence.load_user_context("analyst_001")
    if loaded_context:
        print(f"  ✓ Restored user context: {loaded_context.user_id}")
        print(f"    Previous conversations: {loaded_context.conversation_count}")
    
    # Load conversation history
    loaded_messages = persistence.load_conversation("session_001")
    print(f"  ✓ Restored conversation history: {len(loaded_messages)} messages")
    
    # Continue conversation
    messages2 = [
        Message(role="user", content="Last month's data", timestamp=datetime.now().isoformat()),
        Message(role="assistant", content="Here's the analysis for last month...", timestamp=datetime.now().isoformat()),
    ]
    
    persistence.save_conversation(messages2, "session_002")
    print("  ✓ Saved session 2")
    
    # List all sessions
    sessions = persistence.list_sessions()
    print(f"\n  Total sessions: {len(sessions)}")
    for session_id in sessions:
        msgs = persistence.load_conversation(session_id)
        print(f"    - {session_id}: {len(msgs)} messages")


def example_memory_fallback() -> None:
    """In-memory fallback example."""
    print_section("Example 5: In-Memory Fallback (Development)")
    
    persistence = MemoryPersistence(use_memory_fallback=True)
    
    messages = [
        Message(role="user", content="Testing memory fallback", timestamp=datetime.now().isoformat())
    ]
    
    persistence.save_conversation(messages, "memory_session")
    print("✓ Saved to memory (no file created)")
    
    loaded = persistence.load_conversation("memory_session")
    print(f"✓ Loaded {len(loaded)} messages from memory")
    
    # Verify no file was created
    if os.path.exists("./ai_workspace/memory/persistence.json"):
        print("⚠ Warning: File was created (should not happen with memory fallback)")
    else:
        print("✓ Confirmed: No file created with memory fallback")


def example_performance() -> None:
    """Performance example."""
    print_section("Example 6: Performance Testing")
    
    persistence = MemoryPersistence(
        storage_path="./ai_workspace/memory/persistence_example.json",
        use_memory_fallback=False
    )
    
    # Test with many messages
    messages = [
        Message(role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=datetime.now().isoformat())
        for i in range(500)
    ]
    
    import time
    
    # Save performance
    start = time.time()
    persistence.save_conversation(messages, "perf_test")
    save_time = time.time() - start
    print(f"Save time: {save_time:.3f}s")
    
    # Load performance
    start = time.time()
    loaded = persistence.load_conversation("perf_test")
    load_time = time.time() - start
    print(f"Load time: {load_time:.3f}s")
    print(f"Messages processed: {len(loaded)}")
    
    if save_time < 1.0 and load_time < 1.0:
        print("✓ Performance within acceptable limits (< 1s)")
    else:
        print("⚠ Performance exceeds acceptable limits")


def example_stats() -> None:
    """Statistics example."""
    print_section("Example 7: Statistics")
    
    persistence = MemoryPersistence(
        storage_path="./ai_workspace/memory/persistence_example.json",
        use_memory_fallback=False
    )
    
    stats = persistence.get_stats()
    print("Persistence Statistics:")
    print(f"  Storage path: {stats['storage_path']}")
    print(f"  Storage type: {'Memory' if stats['use_memory_fallback'] else 'File'}")
    print(f"  Cache size: {stats['cache_size']} entries")
    print(f"  Sessions: {stats['sessions_count']}")
    
    if 'file_size' in stats:
        print(f"  File size: {stats['file_size']} bytes")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Memory Persistence Examples")
    parser.add_argument("--memory-fallback", action="store_true",
                       help="Use in-memory fallback instead of file storage")
    parser.add_argument("--storage-path", type=str, default=None,
                       help="Custom storage path")
    parser.add_argument("--example", type=str, default="all",
                       help="Specific example to run (all, basic, context, rag, session, memory, performance, stats)")
    
    args = parser.parse_args()
    
    # Override persistence settings
    if args.memory_fallback:
        print("Using in-memory fallback mode")
    
    # Run examples
    examples = {
        "basic": example_basic_usage,
        "context": example_user_context,
        "rag": example_rag_state,
        "session": example_session_continuity,
        "memory": example_memory_fallback,
        "performance": example_performance,
        "stats": example_stats
    }
    
    if args.example == "all":
        example_basic_usage()
        example_user_context()
        example_rag_state()
        example_session_continuity()
        example_memory_fallback()
        example_performance()
        example_stats()
    elif args.example in examples:
        examples[args.example]()
    else:
        print(f"Unknown example: {args.example}")
        print(f"Available examples: {', '.join(examples.keys())}")
        sys.exit(1)
    
    print_section("All Examples Completed")


if __name__ == "__main__":
    main()
