from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import httpx
import re
from datetime import datetime, timedelta
from ..schemas import ChatRequest, ChatResponse, TableResponse
from ..deps import llm, embedder, vs, sql
from ..services.retrieval import semantic_search
from ..services.charting import plot_table
from ..services.schema_ingestion import retrieve_schema_context
from ..services.query_cache import query_learner
import pandas as pd

router = APIRouter(prefix="/chat", tags=["chat"])

# Store conversation history per session (in production, use Redis or DB)
conversation_history: Dict[str, List[Dict[str, Any]]] = {}

@router.get("/stats")
async def get_chat_stats():
    """Get chat performance and caching statistics."""
    cache_stats = query_learner.get_cache_stats()
    return {
        "status": "operational",
        "cache_size": cache_stats.get("cache_size", 0),
        "cache_hits": cache_stats.get("cache_hits", 0),
        "patterns_learned": cache_stats.get("patterns_learned", {}),
        "features": [
            "auto_source_detection", 
            "dynamic_mode_detection", 
            "query_caching", 
            "pattern_learning", 
            "schema_awareness",
            "conversation_memory",
            "time_filtering"
        ]
    }

@router.get("/history/{session_id}")
async def get_conversation_history(session_id: str):
    """Get conversation history for a session."""
    return {
        "session_id": session_id,
        "messages": conversation_history.get(session_id, [])
    }

@router.delete("/history/{session_id}")
async def clear_conversation_history(session_id: str):
    """Clear conversation history for a session."""
    if session_id in conversation_history:
        del conversation_history[session_id]
    return {"message": f"Conversation history cleared for session {session_id}"}
async def health_check():
    """Check downstream LLM via /health (fast) then fallback to 1-token chat probe."""
    from ..deps import llm  # local import to avoid cycles
    base = llm.base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=15.0) as client:
        # First try /health if exposed
        try:
            r = await client.get(f"{base}/health")
            if r.status_code == 200:
                return {"status": "ok"}
        except Exception:
            pass
        # Fallback probe
        try:
            r = await client.post(f"{base}/v1/chat/completions", json={
                "model": llm.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1
            })
            r.raise_for_status()
            return {"status": "ok"}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"LLM service unavailable: {e}")

SYSTEM = (
    "You are a data assistant. If the question requires math/aggregation (sum, avg, count, top), "
    "write a small SQL for the selected source's warehouse tables. If it's a descriptive question, "
    "summarize from retrieved chunks. Keep answers concise."
)

# Map source -> table names used for NL→SQL examples
SOURCE_TABLES = {
    "financial": "financial_orders",
    "devices": "device_metrics",
}

AGG_KEYWORDS = [
    "how many","how much","count","total","sum","average","avg","mean","min","max",
    "revenue","sales order","sales orders","orders did we get","orders did we receive","number of orders"
]

def detect_source_from_query(message: str) -> str:
    """Detect data source from user query."""
    m = message.lower()
    
    # Financial keywords
    financial_keywords = [
        "order", "orders", "revenue", "sales", "customer", "customers", "payment", "paid", 
        "amount", "money", "price", "invoice", "billing", "financial", "transaction"
    ]
    
    # Device keywords  
    device_keywords = [
        "device", "devices", "sensor", "sensors", "uptime", "online", "offline", 
        "status", "location", "iot", "telemetry", "metrics", "monitoring"
    ]
    
    financial_score = sum(1 for k in financial_keywords if k in m)
    device_score = sum(1 for k in device_keywords if k in m)
    
    if financial_score > device_score:
        return "financial"
    elif device_score > financial_score:
        return "devices"
    else:
        # Default to financial if unclear
        return "financial"

def detect_mode_from_query(message: str) -> str:
    """Detect desired response mode from user query."""
    m = message.lower()
    
    # Chart indicators
    chart_keywords = ["chart", "graph", "plot", "visualize", "visualization", "show me a chart", "create a graph"]
    if any(k in m for k in chart_keywords):
        return "chart"
    
    # Table indicators  
    table_keywords = ["table", "list", "show all", "breakdown", "by location", "by customer", "by status", "group by"]
    if any(k in m for k in table_keywords):
        return "table"
    
    # Text/count indicators (single values)
    text_keywords = ["how many", "count", "total", "sum", "average", "avg", "what is", "tell me"]
    if any(k in m for k in text_keywords):
        return "text"
        
    return "auto"
    """Detect desired response mode from user query."""
    m = message.lower()
    
    # Chart indicators
    chart_keywords = ["chart", "graph", "plot", "visualize", "visualization", "show me a chart", "create a graph"]
    if any(k in m for k in chart_keywords):
        return "chart"
    
    # Table indicators  
    table_keywords = ["table", "list", "show all", "breakdown", "by location", "by customer", "by status", "group by"]
    if any(k in m for k in table_keywords):
        return "table"
    
    # Text/count indicators (single values)
    text_keywords = ["how many", "count", "total", "sum", "average", "avg", "what is", "tell me"]
    if any(k in m for k in text_keywords):
        return "text"
        
    return "auto"

def needs_sql(message: str) -> bool:
    m = message.lower()
    return any(k in m for k in AGG_KEYWORDS)

def build_time_filter(message: str) -> tuple[str, str]:
    """Build time filter SQL and description based on message."""
    m = message.lower()
    now = datetime.now()
    
    # Parse relative time expressions
    if 'past' in m or 'last' in m:
        # Extract number and time unit
        patterns = [
            (r'(\d+)\s*second[s]?', 'seconds'),
            (r'(\d+)\s*minute[s]?', 'minutes'), 
            (r'(\d+)\s*hour[s]?', 'hours'),
            (r'(\d+)\s*day[s]?', 'days'),
            (r'(\d+)\s*week[s]?', 'weeks'),
            (r'(\d+)\s*month[s]?', 'months')
        ]
        
        for pattern, unit in patterns:
            match = re.search(pattern, m)
            if match:
                num = int(match.group(1))
                if unit == 'seconds':
                    cutoff = now - timedelta(seconds=num)
                elif unit == 'minutes':
                    cutoff = now - timedelta(minutes=num)
                elif unit == 'hours':
                    cutoff = now - timedelta(hours=num)
                elif unit == 'days':
                    cutoff = now - timedelta(days=num)
                elif unit == 'weeks':
                    cutoff = now - timedelta(weeks=num)
                elif unit == 'months':
                    cutoff = now - timedelta(days=num*30)  # Approximate
                
                cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')
                filter_sql = f"ts >= '{cutoff_str}'"
                desc = f"past {num} {unit}"
                return filter_sql, desc
    
    # Default to today
    if 'today' in m:
        filter_sql = "DATE_TRUNC('day', ts) = CURRENT_DATE"
        desc = "today"
        return filter_sql, desc
    
    # If no time specified, default to all time but mention it
    return "1=1", "all time"

def build_rule_sql(message: str, source: str) -> str | None:
    """Build SQL for common financial/device queries with time filtering."""
    m = message.lower()
    time_filter, time_desc = build_time_filter(message)
    
    if source == 'financial':
        tbl = 'financial_orders'
        group_by_customer = 'by customer' in m or 'per customer' in m
        wants_status_breakdown = 'status' in m or 'paid' in m or 'refunded' in m or 'cancelled' in m
        
        # Count orders with time filter
        if 'how many' in m or 'number of orders' in m or 'orders did we' in m or ('count' in m and 'order' in m):
            if wants_status_breakdown:
                return f"SELECT status, COUNT(*) AS order_count FROM {tbl} WHERE {time_filter} GROUP BY status ORDER BY order_count DESC;"
            if group_by_customer:
                return f"SELECT customer, COUNT(*) AS order_count FROM {tbl} WHERE {time_filter} GROUP BY customer ORDER BY order_count DESC;"
            return f"SELECT COUNT(*) AS order_count FROM {tbl} WHERE {time_filter};"
        
        # Revenue with time filter
        if 'revenue' in m or ('sum' in m and 'amount' in m) or ('total' in m and 'amount' in m):
            if group_by_customer:
                return f"SELECT customer, SUM(amount) AS total_revenue, COUNT(*) AS order_count FROM {tbl} WHERE {time_filter} GROUP BY customer ORDER BY total_revenue DESC;"
            return f"SELECT SUM(amount) AS total_revenue, COUNT(*) AS order_count FROM {tbl} WHERE {time_filter};"
        
        # Average order value with time filter
        if ('average' in m or 'avg' in m or 'mean' in m) and ('order' in m or 'amount' in m):
            return f"SELECT AVG(amount) AS average_order_value FROM {tbl} WHERE {time_filter};"
        
        # Status breakdown with time filter
        if wants_status_breakdown:
            return f"SELECT status, COUNT(*) AS order_count FROM {tbl} WHERE {time_filter} GROUP BY status ORDER BY order_count DESC;"
            
    elif source == 'devices':
        tbl = 'device_metrics'
        if 'average' in m and ('uptime' in m or 'uptime_minutes' in m):
            return f"SELECT AVG(uptime_minutes) AS average_uptime_minutes FROM {tbl} WHERE {time_filter};"
        if 'uptime' in m and ('by location' in m or 'per location' in m):
            return f"SELECT location, AVG(uptime_minutes) AS average_uptime_minutes FROM {tbl} WHERE {time_filter} GROUP BY location ORDER BY average_uptime_minutes DESC;"
        if 'how many' in m and 'device' in m:
            return f"SELECT COUNT(DISTINCT device_id) AS device_count FROM {tbl} WHERE {time_filter};"
        if 'status' in m or 'online' in m or 'offline' in m:
            return f"SELECT status, COUNT(*) AS device_count FROM {tbl} WHERE {time_filter} GROUP BY status ORDER BY device_count DESC;"
    
    return None

def extract_sql(text: str) -> str | None:
    # Remove code fences
    cleaned = text.replace('```sql', '```').replace('```SQL', '```')
    if '```' in cleaned:
        parts = cleaned.split('```')
        for p in parts:
            if 'select' in p.lower():
                cleaned = p
                break
    # Find first SELECT
    idx = cleaned.lower().find('select')
    if idx == -1:
        return None
    candidate = cleaned[idx:].strip()
    # Ensure ends before any explanation lines starting with non SQL
    return candidate

def normalize_sql(sql_text: str, tbl: str) -> str:
    """SQL normalization with time handling."""
    # Ensure correct table name
    sql_text = sql_text.replace('financial_data', 'financial_orders')
    sql_text = sql_text.replace('devices_data', 'device_metrics')
    
    # Handle time interval syntax for DuckDB
    sql_text = re.sub(r'INTERVAL\s+[\'"](\d+)\s+(\w+)[\'"]', r"INTERVAL '\1 \2'", sql_text, flags=re.IGNORECASE)
    
    # Replace CURRENT_TIMESTAMP - INTERVAL with proper DuckDB syntax
    sql_text = re.sub(
        r'CURRENT_TIMESTAMP\s*-\s*INTERVAL\s+[\'"](\d+)\s+(\w+)[\'"]',
        r"(CURRENT_TIMESTAMP - INTERVAL '\1 \2')",
        sql_text,
        flags=re.IGNORECASE
    )
    
    # If today mentioned but no explicit date filter, add where on CURRENT_DATE
    lower = sql_text.lower()
    if 'today' in lower and "date_trunc('day', ts)" not in lower and 'current_date' not in lower and 'interval' not in lower:
        # Insert before trailing semicolon if present
        if ';' in sql_text:
            parts = sql_text.rsplit(';', 1)
            core = parts[0]
            if ' where ' in core.lower():
                core += " AND DATE_TRUNC('day', ts) = CURRENT_DATE"
            else:
                core += " WHERE DATE_TRUNC('day', ts) = CURRENT_DATE"
            sql_text = core + ';'
        else:
            if ' where ' in lower:
                sql_text += " AND DATE_TRUNC('day', ts) = CURRENT_DATE"
            else:
                sql_text += " WHERE DATE_TRUNC('day', ts) = CURRENT_DATE"
    
    # Basic safety: forbid update/delete
    if any(w in lower for w in [' update ', ' delete ', ' insert ', ' drop ', ' alter ']):
        raise ValueError('Unsafe SQL detected')
    
    return sql_text

@router.post("/ask", response_model=ChatResponse)
async def ask(req: ChatRequest):
    try:
        # Get or create session ID (in production, use proper session management)
        session_id = getattr(req, 'session_id', 'default_session')
        if session_id not in conversation_history:
            conversation_history[session_id] = []
        
        # Add user message to conversation history
        conversation_history[session_id].append({
            "role": "user", 
            "message": req.message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 10 messages for context
        if len(conversation_history[session_id]) > 10:
            conversation_history[session_id] = conversation_history[session_id][-10:]
        
        # Auto-detect source if needed
        actual_source = req.source
        if req.source == "auto":
            actual_source = detect_source_from_query(req.message)
            print(f"[auto_detect] Detected source: {actual_source} for query: {req.message[:50]}...")
        
        # Create context-aware cache key that includes recent conversation
        recent_context = " ".join([msg["message"] for msg in conversation_history[session_id][-3:]])
        cache_key = f"{req.message}|{actual_source}|{req.mode}|{hash(recent_context) % 10000}"
        
        # Check cache with context awareness
        cached_response = await query_learner.get_cached_response(cache_key, actual_source, req.mode)
        if cached_response:
            return ChatResponse(**cached_response)
        
        # 1) Always retrieve schema context first for hybrid approach
        schema_context = await retrieve_schema_context(req.message, actual_source, embedder, vs, top_k=3)
        
        # 2) Dynamic mode detection if user didn't specify
        if req.mode == "auto":
            detected_mode = detect_mode_from_query(req.message)
        else:
            detected_mode = req.mode
        
        # 3) Intent detection with schema context and conversation history
        conversation_context = "\n".join([
            f"{msg['role']}: {msg['message']}" 
            for msg in conversation_history[session_id][-3:]  # Last 3 messages for context
        ])
        
        intent_prompt = [
            {"role": "system", "content": (
                "You are a data analytics assistant. Classify user queries as SQL (for aggregations, counts, analytics) "
                "or RAG (for descriptive questions). Use provided schema context and conversation history to inform your decision.\n"
                f"Available Schema Context:\n{schema_context}\n"
                f"Recent Conversation:\n{conversation_context}\n"
                "Reply with 'SQL' for quantitative queries or 'RAG' for descriptive queries."
            )},
            {"role": "user", "content": req.message}
        ]
        
        mode_hint = 'SQL' if needs_sql(req.message) else 'RAG'
        wants_chart = detected_mode == "chart"
        
        # Use LLM for refined classification with schema awareness
        try:
            intent_raw = (await llm.chat(intent_prompt)).upper()
            if 'SQL' in intent_raw:
                mode_hint = 'SQL'
        except Exception:
            # Fallback to heuristic if LLM fails
            pass

        # 4) SQL path with schema-aware generation and time filtering
        if mode_hint == "SQL":
            tbl = SOURCE_TABLES[actual_source]
            
            # Try rule-based SQL first (with time filtering)
            rule_sql = build_rule_sql(req.message, actual_source)
            if rule_sql:
                sql_text = rule_sql
            else:
                # SQL generation with schema context and conversation history
                sql_prompt = [
                    {"role": "system", "content": (
                        "You are an expert SQL analyst. Generate precise DuckDB SQL queries using the provided schema context and conversation history.\n"
                        f"Schema Context:\n{schema_context}\n"
                        f"Recent Conversation:\n{conversation_context}\n\n"
                        "Rules:\n"
                        "- Use exact table/column names from schema\n"
                        "- Pay attention to time references (today, past X minutes/seconds/hours)\n"  
                        "- For 'past X minutes/seconds', use: ts >= CURRENT_TIMESTAMP - INTERVAL 'X minutes'\n"
                        "- For 'today' queries: WHERE DATE_TRUNC('day', ts) = CURRENT_DATE\n"
                        "- Return ONLY executable SQL (no explanations)\n"
                        "- Use appropriate aggregations (COUNT, SUM, AVG) for analytics\n"
                        "- Group by relevant dimensions when asked for breakdowns\n"
                        "- Consider conversation context for follow-up questions\n"
                    )},
                    {"role": "user", "content": f"Query: {req.message}\nTable: {tbl}\nGenerate SQL:"}
                ]
                
                sql_raw = await llm.chat(sql_prompt)
                sql_text = extract_sql(sql_raw) or sql_raw
                sql_text = normalize_sql(sql_text, tbl)
                
            try:
                df = sql.query(sql_text)
                
                # Result formatting based on detected/requested mode
                if detected_mode == "chart" or wants_chart:
                    if df.shape[1] >= 2 and len(df) > 0:
                        x, y = df.columns[0], df.columns[1]
                        path = plot_table(df, x=x, y=y, kind="bar")
                        # Fix chart path format for frontend
                        chart_filename = path.split('/')[-1] if '/' in path else path
                        response = ChatResponse(mode="chart", chart_path=chart_filename, query_sql=sql_text)
                        
                        # Add assistant response to conversation history
                        conversation_history[session_id].append({
                            "role": "assistant",
                            "message": f"Generated chart from data with {len(df)} records",
                            "chart_path": chart_filename,
                            "sql": sql_text,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        await query_learner.cache_response(cache_key, actual_source, "chart", sql_text, response.dict())
                        return response
                    else:
                        # Not enough data for chart, return text instead
                        summary = _format_sql_result(df, req.message, sql_text)
                        response = ChatResponse(mode="text", text=f"Insufficient data for chart visualization. {summary}", query_sql=sql_text)
                        
                        # Add to conversation history
                        conversation_history[session_id].append({
                            "role": "assistant",
                            "message": response.text,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        await query_learner.cache_response(cache_key, actual_source, "text", sql_text, response.dict())
                        return response
                        
                if detected_mode == "table" and len(df) > 0:
                    response = ChatResponse(mode="table", table=TableResponse(columns=list(df.columns), rows=df.values.tolist()), query_sql=sql_text)
                    
                    # Add to conversation history
                    conversation_history[session_id].append({
                        "role": "assistant",
                        "message": f"Retrieved {len(df)} records in table format",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    await query_learner.cache_response(cache_key, actual_source, "table", sql_text, response.dict())
                    return response
                elif detected_mode == "table" and len(df) == 0:
                    response = ChatResponse(mode="text", text="No data found for the specified criteria.", query_sql=sql_text)
                    
                    # Add to conversation history
                    conversation_history[session_id].append({
                        "role": "assistant",
                        "message": response.text,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    await query_learner.cache_response(cache_key, actual_source, "text", sql_text, response.dict())
                    return response
                
                # Text summarization for single values and small results
                if len(df) == 0:
                    response = ChatResponse(mode="text", text="No data found for the specified criteria.", query_sql=sql_text)
                    
                    # Add to conversation history
                    conversation_history[session_id].append({
                        "role": "assistant",
                        "message": response.text,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    await query_learner.cache_response(cache_key, actual_source, "text", sql_text, response.dict())
                    return response
                
                summary = _format_sql_result(df, req.message, sql_text)
                response = ChatResponse(mode="text", text=summary, query_sql=sql_text)
                
                # Add to conversation history
                conversation_history[session_id].append({
                    "role": "assistant",
                    "message": summary,
                    "timestamp": datetime.now().isoformat()
                })
                
                await query_learner.cache_response(cache_key, actual_source, "text", sql_text, response.dict())
                return response
                
            except Exception as e:
                print(f"[SQL Error] {e} - SQL: {sql_text}")
                # Fallback with schema context
                return await _rag_with_schema_context(ChatRequest(source=actual_source, message=req.message, mode=req.mode, top_k=req.top_k), schema_context)

        # 5) RAG path with schema awareness  
        return await _rag_with_schema_context(ChatRequest(source=actual_source, message=req.message, mode=req.mode, top_k=req.top_k), schema_context)

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error communicating with LLM service: {str(e)}")

def _format_sql_result(df: pd.DataFrame, question: str, sql: str) -> str:
    """Format SQL results based on query type."""
    q_lower = question.lower()
    
    if df.shape[0] == 1 and df.shape[1] == 1:
        # Single value result
        val = df.iloc[0, 0]
        if any(k in q_lower for k in ["how many", "count", "number of"]):
            return f"Count: {int(val)}"
        elif any(k in q_lower for k in ["revenue", "total", "sum"]):
            return f"Total: ${val:,.2f}" if isinstance(val, (int, float)) else f"Total: {val}"
        elif any(k in q_lower for k in ["average", "avg", "mean"]):
            return f"Average: {val:.2f}" if isinstance(val, (int, float)) else f"Average: {val}"
        else:
            return f"Result: {val}"
    
    elif df.shape[0] <= 10:
        # Small result set - show formatted table
        result_lines = [f"Found {len(df)} results:"]
        for _, row in df.iterrows():
            if df.shape[1] == 2:
                result_lines.append(f"• {row.iloc[0]}: {row.iloc[1]}")
            else:
                result_lines.append(f"• {dict(row)}")
        return "\n".join(result_lines)
    
    else:
        # Large result set - summarize
        return f"Query returned {len(df)} rows with columns: {', '.join(df.columns)}. Use table view for details."

async def _rag_with_schema_context(req: ChatRequest, schema_context: str) -> ChatResponse:
    """RAG search with schema context for descriptive questions."""
    top_k = getattr(req, 'top_k', 6) or 6
    
    try:
        # Get semantic hits from vector store
        hits = await semantic_search(embedder, vs, req.source, req.message, top_k)
        
        # Check if we have relevant data
        if not hits or all(h.score < 0.5 for h in hits):
            return ChatResponse(
                mode="text", 
                text=f"I don't have enough relevant information about '{req.message}' in the {req.source} data. Could you try rephrasing your question or ask about specific metrics I can calculate?"
            )
        
        data_context = "\n".join([str(h.payload) for h in hits[:3]])  # Limit data context
        
        # Combine schema and data context
        full_context = f"SCHEMA CONTEXT:\n{schema_context}\n\nDATA CONTEXT:\n{data_context}"
        
        answer_prompt = [
            {"role": "system", "content": (
                "You are a data analytics assistant. Answer questions using the provided schema and data context. "
                "Be concise and helpful. If you don't have relevant data, say so clearly. "
                "For analytical questions, suggest specific SQL queries that could provide the answer."
            )},
            {"role": "user", "content": f"Question: {req.message}\n\nContext:\n{full_context}"}
        ]
        
        answer = await llm.chat(answer_prompt)
        
        # Filter out irrelevant or low-quality responses
        if len(answer.strip()) < 20 or "I don't have" in answer:
            return ChatResponse(
                mode="text", 
                text=f"I don't have sufficient relevant information about '{req.message}' in the {req.source} data. Try asking about specific metrics or data points I can calculate."
            )
        
        return ChatResponse(mode="text", text=answer)
        
    except Exception as e:
        print(f"[rag_with_schema_context error] {e}")
        return ChatResponse(
            mode="text", 
            text=f"I encountered an error processing your query about {req.source} data. Please try rephrasing your question or ask about specific metrics I can calculate."
        )

async def _rag_fallback(req: ChatRequest) -> ChatResponse:
    """Original RAG fallback - kept for compatibility."""
    return await _rag_with_schema_context(req, "")