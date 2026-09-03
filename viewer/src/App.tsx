import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import ShowDetail from './pages/ShowDetail'
import Search from './pages/Search'

function App() {
  return (
    <div className="app-container">
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/show/:slug" element={<ShowDetail />} />
        <Route path="/search" element={<Search />} />
      </Routes>
    </div>
  )
}

export default App
