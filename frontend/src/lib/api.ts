import { AppConfig } from '../config';

interface AskParams {
  source: string;
  message: string;
  mode?: 'auto' | 'text' | 'table' | 'chart';
  top_k?: number;
  session_id?: string;
}

export interface AskResultTable { mode:'table'; table:{ columns:string[]; rows:any[][] }; query_sql?:string }
export interface AskResultChart { mode:'chart'; chart_path:string; query_sql?:string }
export interface AskResultText { mode:'text'; text:string; query_sql?:string }
export type AskResult = AskResultText | AskResultTable | AskResultChart;

export async function ask(params: AskParams): Promise<AskResult> {
  const url = AppConfig.getApiUrl('/chat/ask');
  const resp = await fetch(url, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ 
      source: params.source, 
      message: params.message,
      mode: params.mode || 'auto',
      top_k: params.top_k || 6,
      session_id: params.session_id || generateSessionId()
    })
  });
  if(!resp.ok){
    throw new Error(`Backend error ${resp.status}`);
  }
  const data = await resp.json();
  return data as AskResult;
}

// Simple session ID generator
function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
