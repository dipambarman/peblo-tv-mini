import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import LoginPage from './pages/LoginPage'
import ShowList from './pages/ShowList'
import ShowDetail from './pages/ShowDetail'
import EpisodeList from './pages/EpisodeList'
import PublishPage from './pages/PublishPage'
import Layout from './components/Layout'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('token'))

  useEffect(() => {
    const handleStorage = () => setIsLoggedIn(!!localStorage.getItem('token'))
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [])

  if (!isLoggedIn) {
    return <LoginPage onLogin={() => setIsLoggedIn(true)} />
  }

  return (
    <Layout onLogout={() => { localStorage.removeItem('token'); localStorage.removeItem('user'); setIsLoggedIn(false) }}>
      <Routes>
        <Route path="/" element={<Navigate to="/shows" replace />} />
        <Route path="/shows" element={<ShowList />} />
        <Route path="/shows/:id" element={<ShowDetail />} />
        <Route path="/episodes" element={<EpisodeList />} />
        <Route path="/publish" element={<PublishPage />} />
        <Route path="/login" element={<Navigate to="/shows" replace />} />
        <Route path="*" element={<Navigate to="/shows" replace />} />
      </Routes>
    </Layout>
  )
}

export default App
