import React, { useRef, useState, useEffect, useCallback } from 'react';
import Message from './Message';
import { ask, type AskResult } from '../lib/api';
import './Chat.scss';

interface ChatMessage { 
  id: string; 
  role: 'user' | 'assistant'; 
  content: string; 
  streaming?: boolean;
  chart_path?: string;
  table?: { columns: string[]; rows: any[][] };
  query_sql?: string;
}

function genId(){ return Math.random().toString(36).slice(2); }

interface ChatProps {
  dataSource?: string; // Make optional for auto-detection
}

export default function Chat({ dataSource }: ChatProps = {}) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  const listRef = useRef<HTMLDivElement|null>(null);
  const abortRef = useRef<AbortController|null>(null);

  useEffect(()=> { if(listRef.current){ listRef.current.scrollTop = listRef.current.scrollHeight; } }, [messages]);

  const streamAppend = useCallback((id:string, full:string)=>{
    setMessages(m=> m.map(msg=> msg.id===id ? {...msg, content:full} : msg));
  },[]);

  async function onSend(){
    const q = input.trim(); if(!q || loading) return;
    setInput('');
    const userMsg:ChatMessage = {id:genId(), role:'user', content:q};
    setMessages(m=>[...m, userMsg]);
    const assistantId = genId();
    setMessages(m=>[...m,{id:assistantId, role:'assistant', content:'', streaming:true}]);
    setLoading(true);
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      // Use auto source detection with session management
      const res:AskResult = await ask({ 
        source: dataSource || 'auto', 
        message: q,
        session_id: sessionId
      });
      
      // Create assistant message based on response type
      if (res.mode === 'text' && res.text) {
        const full = res.text;
        let acc = '';
        for (const ch of full) {
          acc += ch;
          streamAppend(assistantId, acc);
          await new Promise(r => setTimeout(r, 12));
          if (controller.signal.aborted) return;
        }
      } else if (res.mode === 'table' && res.table) {
        // Update message with table data
        setMessages(m=> m.map(msg=> msg.id===assistantId ? {
          ...msg, 
          content: `Data retrieved successfully (${res.table.rows.length} rows)`,
          table: res.table,
          query_sql: res.query_sql,
          streaming: false
        } : msg));
      } else if (res.mode === 'chart' && res.chart_path) {
        // Update message with chart data - fix chart path handling
        setMessages(m=> m.map(msg=> msg.id===assistantId ? {
          ...msg, 
          content: `Chart generated from your data`,
          chart_path: res.chart_path,
          query_sql: res.query_sql,
          streaming: false
        } : msg));
      }
      
      if (res.mode === 'text') {
        setMessages(m=> m.map(msg=> msg.id===assistantId ? {...msg, streaming:false} : msg));
      }
    } catch(e:any){
      if(controller.signal.aborted) return;
      streamAppend(assistantId, `Error: ${e.message}`);
      setMessages(m=> m.map(msg=> msg.id===assistantId ? {...msg, streaming:false} : msg));
    } finally { if(!controller.signal.aborted) setLoading(false); }
  }

  function onKey(e:React.KeyboardEvent<HTMLTextAreaElement>){
    if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); onSend(); }
  }

  function stop(){ abortRef.current?.abort(); setLoading(false); }
  function copyToClipboard(text:string){ navigator.clipboard?.writeText(text).catch(()=>{}); }

  return (
    <div className="chat-container">

      <div ref={listRef} className="messages-container" role="log" aria-live="polite">
        {messages.map(m=> <Message 
          key={m.id} 
          role={m.role} 
          content={m.content} 
          streaming={!!m.streaming} 
          onCopy={copyToClipboard}
          chart_path={m.chart_path}
          table={m.table}
          query_sql={m.query_sql}
        />)}
        {loading && <div className="typing-indicator" aria-label="Model is thinking"><span/><span/><span/></div>}
      </div>
      <form className="input-form" onSubmit={e=>{e.preventDefault(); onSend();}}>
        <textarea
          aria-label="Message input"
          value={input}
          onChange={e=>setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="Ask anything about your data... (Shift+Enter for newline)"
          className="chat-input"
          rows={1}
        />
        {loading && <button type="button" onClick={stop} className="send-button" style={{background:'linear-gradient(135deg,#ef4444,#f87171)'}}>Stop</button>}
        <button type="submit" className="send-button" disabled={loading || !input.trim()}>Send</button>
      </form>
    </div>
  );
}