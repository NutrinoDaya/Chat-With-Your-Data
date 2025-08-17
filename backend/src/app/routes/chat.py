"""
Chat API Routes

This module provides the main chat API endpoints with clean, modular architecture.
All business logic has been extracted to utility modules for maintainability.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import pandas as pd

# Schema and dependency imports
from ..schemas import ChatRequest, ChatResponse, TableResponse
from ..deps import llm, embedder, vs, sql
from ..services.charting import plot_table
from ..services.schema_ingestion import retrieve_schema_context
from ..services.query_cache import query_learner

# Utility module imports
from ..utils.query_detection import (
    detect_source_from_query,
    detect_mode_from_query,
    is_greeting_or_social,
    get_greeting_response
)
from ..utils.sql_generation import (
    build_rule_sql,
    extract_sql,
    normalize_sql,
    add_limit_to_llm_sql,
    SOURCE_TABLES
)
from ..utils.response_formatting import (
    format_sql_result,
    create_table_response,
    should_use_chart,
    determine_chart_columns,
    format_chart_filename,
    validate_dataframe
)
from ..utils.conversation_manager import (
    add_message_to_history,
    get_conversation_history,
    clear_conversation_history,
    build_conversation_context,
    create_cache_key,
    get_session_stats
)
from ..utils.rag_processing import (
    process_rag_with_schema_context,
    process_rag_fallback,
    detect_query_intent
)
from ..utils.health_checks import (
    check_llm_health,
    get_system_health
)

# Initialize router
router = APIRouter(prefix="/chat", tags=["chat"])

# Constants
SYSTEM_PROMPT = (
    "You are a data assistant. If the question requires math/aggregation (sum, avg, count, top), "
    "write a small SQL for the selected source's warehouse tables. If it's a descriptive question, "
    "summarize from retrieved chunks. Keep answers concise."
)


@router.get("/stats")
async def get_chat_stats():
    """Get chat performance and caching statistics."""
    cache_stats = query_learner.get_cache_stats()
    session_stats = get_session_stats()
    
    return {
        "status": "operational",
        "cache_size": cache_stats.get("cache_size", 0),
        "cache_hits": cache_stats.get("cache_hits", 0),
        "patterns_learned": cache_stats.get("patterns_learned", {}),
        "session_stats": session_stats,
        "features": [
            "auto_source_detection", 
            "dynamic_mode_detection", 
            "query_caching", 
            "pattern_learning", 
            "schema_awareness",
            "conversation_memory",
            "time_filtering",
            "greeting_detection",
            "limit_clause_enforcement"
        ]
    }


@router.get("/history/{session_id}")
async def get_conversation_history_endpoint(session_id: str):
    """Get conversation history for a session."""
    messages = get_conversation_history(session_id)
    return {
        "session_id": session_id,
        "messages": messages
    }


@router.delete("/history/{session_id}")
async def clear_conversation_history_endpoint(session_id: str):
    """Clear conversation history for a session."""
    cleared = clear_conversation_history(session_id)
    status = "cleared" if cleared else "not_found"
    return {"message": f"Conversation history {status} for session {session_id}"}


@router.get("/health")
async def health_check():
    """Check system health including LLM availability."""
    try:
        llm_status = await check_llm_health(llm)
        system_status = await get_system_health()
        
        return {
            "status": "healthy",
            "llm": llm_status,
            "system": system_status
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {e}")


@router.post("/ask", response_model=ChatResponse)
async def ask(req: ChatRequest):
    """
    Main chat endpoint that handles user queries with intelligent routing.
    
    This function orchestrates the entire chat pipeline:
    1. Session management and conversation history
    2. Greeting detection for social interactions
    3. Source and mode detection
    4. Intent detection (SQL vs RAG)
    5. Query processing and response generation
    6. Result formatting and caching
    """
    try:
        # Get or create session ID
        session_id = getattr(req, 'session_id', 'default_session')
        
        # Add user message to conversation history
        add_message_to_history(session_id, req.message, "user")
        
        # Handle greetings and social interactions
        if is_greeting_or_social(req.message):
            response_text = get_greeting_response(req.message)
            return ChatResponse(
                mode="text",
                text=response_text,
                table=None,
                chart_path=None,
                query_sql=None
            )
        
        # Auto-detect source if needed
        actual_source = req.source
        if req.source == "auto":
            actual_source = detect_source_from_query(req.message)
            print(f"[auto_detect] Detected source: {actual_source} for query: {req.message[:50]}...")
        
        # Build conversation context and cache key
        conversation_context = build_conversation_context(session_id)
        cache_key = create_cache_key(req.message, actual_source, req.mode, session_id)
        
        # Check cache first
        cached_response = await query_learner.get_cached_response(cache_key, actual_source, req.mode)
        if cached_response:
            return ChatResponse(**cached_response)
        
        # Retrieve schema context for better responses
        schema_context = await retrieve_schema_context(req.message, actual_source, embedder, vs, top_k=3)
        
        # Detect response mode if auto
        detected_mode = detect_mode_from_query(req.message) if req.mode == "auto" else req.mode
        
        # Detect query intent (SQL vs RAG)
        intent = await detect_query_intent(req.message, schema_context, conversation_context)
        
        if intent == "SQL":
            # Process SQL-based queries
            response = await _process_sql_query(req, actual_source, detected_mode, schema_context)
        else:
            # Process RAG-based queries
            response = await process_rag_with_schema_context(req, schema_context, conversation_context)
        
        # Cache successful responses
        if response and (response.text or response.table):
            await query_learner.cache_response(
                req.message, 
                actual_source, 
                detected_mode, 
                response.query_sql,
                response.dict()
            )
        
        # Add assistant response to conversation history
        response_text = response.text or "Generated data visualization"
        add_message_to_history(session_id, response_text, "assistant")
        
        return response
        
    except Exception as e:
        print(f"[chat_error] {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


async def _process_sql_query(
    req: ChatRequest,
    source: str,
    mode: str,
    schema_context: str
) -> ChatResponse:
    """
    Process SQL-based queries with rule-based and LLM fallback.
    
    Args:
        req: Chat request object
        source: Detected data source
        mode: Detected response mode
        schema_context: Schema documentation context
        
    Returns:
        ChatResponse with SQL query results
    """
    table_name = SOURCE_TABLES.get(source, "financial_orders")
    
    # Try rule-based SQL generation first
    sql_text = build_rule_sql(req.message, source)
    
    if not sql_text:
        # Fallback to LLM-generated SQL
        sql_text = await _generate_llm_sql(req, table_name, schema_context)
    
    if not sql_text:
        # If no SQL could be generated, fall back to RAG
        return await process_rag_fallback(req)
    
    try:
        # Execute SQL query
        df = sql.query(sql_text)
        
        if not validate_dataframe(df):
            return ChatResponse(
                mode="text",
                text="No data found for your query.",
                table=None,
                chart_path=None,
                query_sql=sql_text
            )
        
        # Generate appropriate response based on mode
        return _format_sql_response(df, req.message, sql_text, mode)
        
    except Exception as e:
        print(f"[sql_error] Query failed: {e}")
        return ChatResponse(
            mode="text",
            text=f"I encountered an error executing your query: {str(e)}",
            table=None,
            chart_path=None,
            query_sql=sql_text
        )


async def _generate_llm_sql(req: ChatRequest, table_name: str, schema_context: str) -> str:
    """
    Generate SQL using LLM with schema context.
    
    Args:
        req: Chat request object
        table_name: Target table name
        schema_context: Schema documentation context
        
    Returns:
        Generated SQL query string
    """
    sql_prompt = [
        {"role": "system", "content": (
            f"{SYSTEM_PROMPT}\n\n"
            f"Schema context:\n{schema_context}\n\n"
            "Generate clean SQL for the user's question. Rules:\n"
            "- Use proper table and column names from schema\n"
            "- Include appropriate WHERE, GROUP BY, ORDER BY clauses\n"
            "- Use COALESCE for NULL safety in aggregations\n"
            "- Group by relevant dimensions when asked for breakdowns\n"
            "- Consider conversation context for follow-up questions\n"
        )},
        {"role": "user", "content": f"Query: {req.message}\nTable: {table_name}\nGenerate SQL:"}
    ]
    
    try:
        sql_raw = await llm.chat(sql_prompt)
        sql_text = extract_sql(sql_raw) or sql_raw
        sql_text = normalize_sql(sql_text, table_name)
        
        # Post-process to add missing LIMIT clauses
        sql_text = add_limit_to_llm_sql(sql_text, req.message)
        
        return sql_text
    except Exception as e:
        print(f"[llm_sql_error] {e}")
        return ""


def _format_sql_response(df: pd.DataFrame, question: str, sql: str, mode: str) -> ChatResponse:
    """
    Format SQL query results into appropriate response format.
    
    Args:
        df: Query result DataFrame
        question: Original user question
        sql: SQL query executed
        mode: Response mode
        
    Returns:
        Formatted ChatResponse
    """
    # Check if chart is requested and appropriate
    if should_use_chart(df, mode, question):
        try:
            x_col, y_col = determine_chart_columns(df)
            chart_path = plot_table(df, x=x_col, y=y_col, kind="bar")
            chart_filename = format_chart_filename(chart_path)
            
            return ChatResponse(
                mode="chart",
                chart_path=chart_filename,
                query_sql=sql,
                text=None,
                table=None
            )
        except Exception as e:
            print(f"[chart_error] {e}")
            # Fall through to table/text response
    
    # For table mode or multiple rows, return table format
    if mode == "table" or len(df) > 1:
        table_data = create_table_response(df)
        return ChatResponse(
            mode="table",
            table=TableResponse(**table_data),
            query_sql=sql,
            text=None,
            chart_path=None
        )
    
    # For single values or text mode, return formatted text
    formatted_text = format_sql_result(df, question, sql)
    return ChatResponse(
        mode="text",
        text=formatted_text,
        query_sql=sql,
        table=None,
        chart_path=None
    )
