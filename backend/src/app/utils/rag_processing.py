"""
RAG (Retrieval-Augmented Generation) Processing Utilities

This module handles RAG-based query processing for descriptive questions
that don't require SQL execution.
"""

from typing import List, Dict, Any
from ..schemas import ChatRequest, ChatResponse
from ..deps import llm, embedder, vs
from ..services.retrieval import semantic_search


async def process_rag_with_schema_context(
    req: ChatRequest, 
    schema_context: str,
    conversation_context: str = ""
) -> ChatResponse:
    """
    Process RAG query with schema context for better responses.
    
    Args:
        req: Chat request object
        schema_context: Schema documentation context
        conversation_context: Recent conversation context
        
    Returns:
        ChatResponse with RAG-generated content
    """
    # Retrieve relevant documentation chunks
    chunks = await semantic_search(req.message, req.source or "auto", embedder, vs, top_k=req.top_k)
    
    if not chunks:
        return await process_rag_fallback(req)
    
    # Build context-aware prompt
    context_text = "\n".join([f"Doc {i+1}: {chunk}" for i, chunk in enumerate(chunks)])
    
    prompt_parts = [
        "You are a helpful data assistant. Answer based on the provided context.",
        f"Schema Context:\n{schema_context}",
        f"Documentation Context:\n{context_text}"
    ]
    
    if conversation_context:
        prompt_parts.insert(-1, f"Recent Conversation:\n{conversation_context}")
    
    prompt_parts.extend([
        f"User Question: {req.message}",
        "Provide a helpful, accurate answer based on the context."
    ])
    
    system_prompt = "\n\n".join(prompt_parts)
    
    try:
        response_text = await llm.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.message}
        ])
        
        return ChatResponse(
            mode="text",
            text=response_text,
            table=None,
            chart_path=None,
            query_sql=None
        )
    except Exception as e:
        print(f"[rag_error] Schema-aware RAG failed: {e}")
        return await process_rag_fallback(req)


async def process_rag_fallback(req: ChatRequest) -> ChatResponse:
    """
    Fallback RAG processing without schema context.
    
    Args:
        req: Chat request object
        
    Returns:
        ChatResponse with basic RAG-generated content
    """
    try:
        # Retrieve relevant chunks
        chunks = await semantic_search(req.message, req.source or "auto", embedder, vs, top_k=req.top_k)
        
        if chunks:
            context_text = "\n".join([f"Context {i+1}: {chunk}" for i, chunk in enumerate(chunks)])
            prompt = (
                f"Based on the following context, answer the user's question:\n\n"
                f"{context_text}\n\n"
                f"Question: {req.message}\n\n"
                f"Answer:"
            )
        else:
            prompt = f"Answer this question about data analytics: {req.message}"
        
        response_text = await llm.chat([
            {"role": "system", "content": "You are a helpful data assistant."},
            {"role": "user", "content": prompt}
        ])
        
        return ChatResponse(
            mode="text",
            text=response_text,
            table=None,
            chart_path=None,
            query_sql=None
        )
    except Exception as e:
        print(f"[rag_fallback_error] {e}")
        return ChatResponse(
            mode="text",
            text="I apologize, but I'm having trouble processing your request right now. Please try again.",
            table=None,
            chart_path=None,
            query_sql=None
        )


def build_intent_detection_prompt(
    message: str,
    schema_context: str,
    conversation_context: str
) -> List[Dict[str, str]]:
    """
    Build prompt for intent detection (SQL vs RAG).
    
    Args:
        message: User message
        schema_context: Available schema context
        conversation_context: Recent conversation history
        
    Returns:
        List of message dictionaries for LLM prompt
    """
    system_content = (
        "You are a data analytics assistant. Classify user queries as SQL (for aggregations, counts, analytics) "
        "or RAG (for descriptive questions). Use provided schema context and conversation history to inform your decision.\n"
        f"Available Schema Context:\n{schema_context}\n"
        f"Recent Conversation:\n{conversation_context}\n"
        "Reply with 'SQL' for quantitative queries or 'RAG' for descriptive queries."
    )
    
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": message}
    ]


async def detect_query_intent(
    message: str,
    schema_context: str,
    conversation_context: str
) -> str:
    """
    Detect whether query needs SQL or RAG processing.
    
    Args:
        message: User message
        schema_context: Available schema context
        conversation_context: Recent conversation history
        
    Returns:
        'SQL' or 'RAG' based on intent detection
    """
    try:
        intent_prompt = build_intent_detection_prompt(message, schema_context, conversation_context)
        intent_response = await llm.chat(intent_prompt)
        
        # Parse intent response
        if 'SQL' in intent_response.upper():
            return 'SQL'
        else:
            return 'RAG'
    except Exception as e:
        print(f"[intent_detection_error] {e}")
        # Default fallback logic
        sql_keywords = ['how many', 'count', 'total', 'sum', 'average', 'revenue', 'amount']
        if any(keyword in message.lower() for keyword in sql_keywords):
            return 'SQL'
        return 'RAG'
