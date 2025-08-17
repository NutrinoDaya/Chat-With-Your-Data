export interface ChatResponse {
  mode: 'text' | 'table' | 'chart';
  text?: string;
  table?: {
    columns: string[];
    rows: any[][];
  };
  chart_path?: string;
  query_sql?: string;
}

export interface AskRequest {
  message: string;
  source: string;
  mode?: 'auto' | 'table' | 'chart';
  top_k?: number;
}

export interface AskResult extends ChatResponse {}
