"""Query caching and pattern learning for improved performance."""

import hashlib
import json
import time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict
import asyncio

@dataclass
class QueryCache:
    """Cache entry for queries and responses."""
    query_hash: str
    original_query: str
    source: str
    mode: str
    sql_query: Optional[str]
    response_data: Dict[str, Any]
    timestamp: float
    hit_count: int = 1
    
class QueryPatternLearner:
    """Learn and cache query patterns for faster responses."""
    
    def __init__(self):
        self.cache: Dict[str, QueryCache] = {}
        self.pattern_learning: Dict[str, List[str]] = {
            "financial_patterns": [],
            "device_patterns": [],
            "successful_queries": []
        }
        self.max_cache_size = 1000
        self.cache_ttl = 3600  # 1 hour
    
    def _hash_query(self, query: str, source: str, mode: str) -> str:
        """Generate hash for query caching."""
        content = f"{query.lower().strip()}:{source}:{mode}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_cached_response(self, query: str, source: str, mode: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired."""
        query_hash = self._hash_query(query, source, mode)
        
        if query_hash in self.cache:
            cache_entry = self.cache[query_hash]
            current_time = time.time()
            
            # Check if cache is still valid
            if current_time - cache_entry.timestamp < self.cache_ttl:
                cache_entry.hit_count += 1
                print(f"[cache_hit] Query: {query[:50]}... (hits: {cache_entry.hit_count})")
                return cache_entry.response_data
            else:
                # Remove expired entry
                del self.cache[query_hash]
        
        return None
    
    async def cache_response(self, query: str, source: str, mode: str, sql_query: Optional[str], response_data: Dict[str, Any]):
        """Cache successful query response."""
        query_hash = self._hash_query(query, source, mode)
        
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.max_cache_size:
            oldest_hash = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_hash]
        
        cache_entry = QueryCache(
            query_hash=query_hash,
            original_query=query,
            source=source,
            mode=mode,
            sql_query=sql_query,
            response_data=response_data,
            timestamp=time.time()
        )
        
        self.cache[query_hash] = cache_entry
        
        # Learn patterns from successful queries
        await self._learn_pattern(query, source, sql_query)
        
        print(f"[cache_store] Cached query: {query[:50]}...")
    
    async def _learn_pattern(self, query: str, source: str, sql_query: Optional[str]):
        """Learn patterns from successful queries."""
        query_lower = query.lower()
        
        # Store patterns by source
        pattern_key = f"{source}_patterns"
        if pattern_key in self.pattern_learning:
            self.pattern_learning[pattern_key].append(query_lower)
            
            # Keep only recent patterns (last 100)
            if len(self.pattern_learning[pattern_key]) > 100:
                self.pattern_learning[pattern_key] = self.pattern_learning[pattern_key][-100:]
        
        # Store successful SQL queries for learning
        if sql_query:
            self.pattern_learning["successful_queries"].append({
                "query": query_lower,
                "sql": sql_query,
                "source": source,
                "timestamp": time.time()
            })
            
            # Keep only recent successful queries
            if len(self.pattern_learning["successful_queries"]) > 200:
                self.pattern_learning["successful_queries"] = self.pattern_learning["successful_queries"][-200:]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(entry.hit_count for entry in self.cache.values())
        
        return {
            "cache_size": len(self.cache),
            "total_hits": total_hits,
            "avg_hits_per_query": total_hits / len(self.cache) if self.cache else 0,
            "patterns_learned": {
                "financial": len(self.pattern_learning.get("financial_patterns", [])),
                "devices": len(self.pattern_learning.get("device_patterns", [])),
                "successful_queries": len(self.pattern_learning.get("successful_queries", []))
            }
        }
    
    async def get_similar_queries(self, query: str, source: str, limit: int = 5) -> List[str]:
        """Get similar queries for suggestions."""
        query_words = set(query.lower().split())
        pattern_key = f"{source}_patterns"
        
        if pattern_key not in self.pattern_learning:
            return []
        
        similar_queries = []
        for cached_query in self.pattern_learning[pattern_key]:
            cached_words = set(cached_query.split())
            similarity = len(query_words.intersection(cached_words)) / len(query_words.union(cached_words))
            
            if similarity > 0.3:  # 30% similarity threshold
                similar_queries.append((cached_query, similarity))
        
        # Sort by similarity and return top results
        similar_queries.sort(key=lambda x: x[1], reverse=True)
        return [q[0] for q in similar_queries[:limit]]

# Global instance
query_learner = QueryPatternLearner()
