#!/usr/bin/env python3
"""
Comprehensive test script for testing all RAG system components
"""
import os
import requests
import json
import time
import sys
from datetime import datetime

class RAGSystemTester:
    def __init__(self):
        self.results = {}
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def log(self, service, status, message):
        """Test results logging"""
        symbol = "✅" if status == "OK" else "❌"
        print(f"{symbol} {service:30} [{status:6}] {message}")
        self.results[service] = {"status": status, "message": message}
        
    def test_qdrant(self):
        """Test Qdrant vector database"""
        try:
            url = "http://localhost:6333/collections"
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 404]:  # 404 OK for empty DB
                self.log("Qdrant", "OK", f"Status: {response.status_code}")
                return True
            else:
                self.log("Qdrant", "FAIL", f"HTTP {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.log("Qdrant", "DOWN", "Connection refused on port 6333")
            return False
        except Exception as e:
            self.log("Qdrant", "ERROR", str(e))
            return False
    
    def test_llm_server(self):
        """Test LLM Server"""
        try:
            llm_endpoint = os.getenv("LLM_ENDPOINT", "http://localhost:8080/v1/chat/completions")
            url = llm_endpoint.replace("/chat/completions", "/models")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "unknown") for m in models]
                self.log("LLM Server", "OK", f"Models: {', '.join(model_names[:1])}")
                return True
            else:
                self.log("LLM Server", "FAIL", f"HTTP {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.log("LLM Server", "DOWN", "Connection refused on port 8080")
            return False
        except Exception as e:
            self.log("LLM Server", "ERROR", str(e))
            return False
    
    def test_embedding_server(self):
        """Test Embedding Server"""
        try:
            embedding_endpoint = os.getenv("EMBEDDING_ENDPOINT", "http://localhost:8090/v1/embeddings")
            url = embedding_endpoint.replace("/v1/embeddings", "/v1/models")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "unknown") for m in models]
                self.log("Embedding Server", "OK", f"Models: {', '.join(model_names[:1])}")
                return True
            else:
                self.log("Embedding Server", "FAIL", f"HTTP {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.log("Embedding Server", "DOWN", "Connection refused on port 8090")
            return False
        except Exception as e:
            self.log("Embedding Server", "ERROR", str(e))
            return False
    
    def test_embedding_endpoint(self):
        """Test embedding endpoint"""
        try:
            embedding_endpoint = os.getenv("EMBEDDING_ENDPOINT", "http://localhost:8090/v1/embeddings")
            url = embedding_endpoint
            payload = {
                "model": "nomic-embed-text-v1.5.Q4_K_M.gguf",
                "input": "test text"
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    embedding = data["data"][0].get("embedding", [])
                    self.log("Embedding Endpoint", "OK", f"Embedding size: {len(embedding)}")
                    return True
                else:
                    self.log("Embedding Endpoint", "FAIL", "No embedding in response")
                    return False
            else:
                self.log("Embedding Endpoint", "FAIL", f"HTTP {response.status_code}")
                return False
        except requests.exceptions.Timeout:
            self.log("Embedding Endpoint", "TIMEOUT", "Request took too long")
            return False
        except Exception as e:
            self.log("Embedding Endpoint", "ERROR", str(e))
            return False
    
    def test_rag_api_health(self):
        """Test RAG API health"""
        try:
            rag_port = os.getenv("RAG_SERVER_PORT", "8000")
            url = f"http://localhost:{rag_port}/health"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                self.log("RAG API /health", "OK", "API is alive")
                return True
            else:
                self.log("RAG API /health", "FAIL", f"HTTP {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.log("RAG API /health", "DOWN", "Connection refused on port 8000")
            return False
        except Exception as e:
            self.log("RAG API /health", "ERROR", str(e))
            return False
    
    def test_rag_api_metrics(self):
        """Test RAG API metrics"""
        try:
            rag_port = os.getenv("RAG_SERVER_PORT", "8000")
            url = f"http://localhost:{rag_port}/metrics"
            response = requests.get(url, timeout=10)
            if response.status_code in [200]:
                self.log("RAG API /metrics", "OK", "Metrics available")
                return True
            else:
                self.log("RAG API /metrics", "FAIL", f"HTTP {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.log("RAG API /metrics", "DOWN", "RAG API not responding")
            return False
        except Exception as e:
            self.log("RAG API /metrics", "ERROR", str(e))
            return False
    
    def test_chat_completion(self):
        """Test chat completions endpoint"""
        try:
            rag_port = os.getenv("RAG_SERVER_PORT", "8000")
            url = f"http://localhost:{rag_port}/v1/chat/completions"
            payload = {
                "model": "Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello!"}
                ],
                "temperature": 0.7,
                "max_tokens": 100
            }
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code in [200]:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    self.log("RAG API /v1/chat/completions", "OK", "Chat response received")
                    return True
                else:
                    self.log("RAG API /v1/chat/completions", "FAIL", "No choices in response")
                    return False
            else:
                self.log("RAG API /v1/chat/completions", "FAIL", f"HTTP {response.status_code}")
                return False
        except requests.exceptions.Timeout:
            self.log("RAG API /v1/chat/completions", "TIMEOUT", "Request took too long")
            return False
        except Exception as e:
            self.log("RAG API /v1/chat/completions", "ERROR", str(e))
            return False
    
    def test_rag_query(self):
        """Test RAG query"""
        try:
            rag_port = os.getenv("RAG_SERVER_PORT", "8000")
            url = f"http://localhost:{rag_port}/rag/query"
            payload = {
                "query": "What is machine learning?",
                "top_k": 5
            }
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.log("RAG API /rag/query", "OK", "Query executed successfully")
                return True
            else:
                self.log("RAG API /rag/query", "FAIL", f"HTTP {response.status_code}")
                return False
        except requests.exceptions.Timeout:
            self.log("RAG API /rag/query", "TIMEOUT", "Query took too long")
            return False
        except Exception as e:
            self.log("RAG API /rag/query", "ERROR", str(e))
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print(f"🧪 RAG SYSTEM COMPLETE TEST | {self.timestamp}")
        print("="*70 + "\n")
        
        # Infrastructure tests
        print("📡 INFRASTRUCTURE TESTS:")
        qdrant_ok = self.test_qdrant()
        llm_ok = self.test_llm_server()
        embedding_ok = self.test_embedding_server()
        
        # Functional tests
        print("\n🔧 FUNCTIONAL TESTS:")
        embedding_endpoint_ok = self.test_embedding_endpoint() if embedding_ok else False
        
        # RAG API tests
        print("\n🚀 RAG API TESTS:")
        health_ok = self.test_rag_api_health()
        metrics_ok = self.test_rag_api_metrics() if health_ok else False
        chat_ok = self.test_chat_completion() if health_ok else False
        query_ok = self.test_rag_query() if health_ok else False
        
        # Summary
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r["status"] == "OK")
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {total - passed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%\n")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! System is fully functional.")
            return 0
        else:
            print("⚠️  Some tests failed. Check the details above.")
            return 1

if __name__ == "__main__":
    tester = RAGSystemTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
