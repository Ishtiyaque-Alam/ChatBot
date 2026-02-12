import { Routes, Route } from 'react-router-dom'
import Homepage from './pages/Homepage'
import ChatbotPage from './pages/ChatbotPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Homepage />} />
      <Route path="/chat" element={<ChatbotPage />} />
    </Routes>
  )
}
