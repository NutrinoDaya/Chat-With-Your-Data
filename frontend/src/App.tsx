import React from 'react'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  const [page, setPage] = React.useState<'chat'|'settings'>('chat')
  return (
      <main>
        {page==='chat' ? <ChatPage/> : <SettingsPage/>}
      </main>
  )
}