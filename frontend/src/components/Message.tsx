import React from 'react';
import './Chat.scss';

interface MessageProps { 
  role: 'user' | 'assistant'; 
  content: any; 
  streaming?: boolean; 
  onCopy?: (text:string)=>void;
  chart_path?: string;
  table?: { columns: string[]; rows: any[][] };
  query_sql?: string;
}

export default function Message({ role, content, streaming, onCopy, chart_path, table, query_sql }: MessageProps){
  const plain = typeof content === 'string' ? content : '';
  
  return (
    <div className={`message-item ${role}`}>      
      <div className="message-content" data-streaming={streaming || undefined}>
        {content}
        
        {/* Display chart if available */}
        {chart_path && (
          <div className="chart-container">
            <img 
              src={`http://localhost:8001/static/charts/${chart_path}`} 
              alt="Generated Chart" 
              className="chart-image"
              onError={(e) => {
                console.error('Failed to load chart image:', chart_path);
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            {query_sql && (
              <details className="sql-details">
                <summary>View SQL Query</summary>
                <pre className="sql-code">{query_sql}</pre>
              </details>
            )}
          </div>
        )}
        
        {/* Display table if available */}
        {table && (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  {table.columns.map((col, i) => (
                    <th key={i}>
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, i) => (
                  <tr key={i}>
                    {row.map((cell, j) => (
                      <td key={j}>
                        {typeof cell === 'number' ? cell.toLocaleString() : cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {query_sql && (
              <details className="sql-details">
                <summary>View SQL Query</summary>
                <pre className="sql-code">{query_sql}</pre>
              </details>
            )}
          </div>
        )}
      </div>
      <div className="message-actions">
        {plain && <button className="icon-btn" title="Copy" onClick={()=> onCopy?.(plain)}>⧉</button>}
      </div>
    </div>
  );
}