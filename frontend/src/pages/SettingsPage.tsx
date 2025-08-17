import React from 'react'
import './SettingsPage.scss'

export default function SettingsPage() {
  return (
    <div className="settings-page">
      <div className="settings-card">
        <h3>Settings</h3>
        <p>
          Configure your providers and endpoints. For OpenAI, set <code>OPENAI_API_KEY</code>; for local, use Ollama.
        </p>
        <ul>
          <li><strong>LLM Provider:</strong> OPENAI or OLLAMA</li>
          <li><strong>Embeddings Provider:</strong> OPENAI or OLLAMA</li>
          <li><strong>Qdrant URL:</strong> Set in <code>.env</code></li>
        </ul>
        <div className="settings-note">
          <span>ℹ️</span> Changes require a restart of backend services.
        </div>
      </div>
    </div>
  )
}