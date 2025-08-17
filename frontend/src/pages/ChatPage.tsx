import React from 'react';
import Chat from '../components/Chat';
import { AppConfig } from '../config';
import './ChatPage.scss';

export default function ChatPage() {
  return (
    <div className="chat-page" style={{ 
      fontFamily: AppConfig.ui.fontFamily,
      fontSize: AppConfig.ui.fontSize 
    }}>
      <header className="chat-header">
        <h1>Data Analytics Assistant</h1>
        <p>Ask questions about your financial data. I'll automatically detect the right data source and response format.</p>
      </header>
      <main className="chat-main">
        <Chat />
      </main>
    </div>
  );
}