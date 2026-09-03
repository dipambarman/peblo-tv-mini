import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { catalogApi } from '../api/catalog'
import { Search as SearchIcon } from 'lucide-react'

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') || ''
  const category = searchParams.get('category') || ''
  
  const [inputValue, setInputValue] = useState(q)

  // Debounce input to URL query
  useEffect(() => {
    const timer = setTimeout(() => {
      if (inputValue !== q) {
        setSearchParams(prev => {
          if (inputValue) prev.set('q', inputValue)
          else prev.delete('q')
          return prev
        }, { replace: true })
      }
    }, 500)
    return () => clearTimeout(timer)
  }, [inputValue, q, setSearchParams])

  const { data, isLoading } = useQuery({
    queryKey: ['search', { q, category }],
    queryFn: () => catalogApi.search({ q, category }),
    enabled: q.length > 0 || category.length > 0,
  })

  const results = data?.data?.results || []

  return (
    <div className="search-container">
      <div className="search-input-wrapper">
        <SearchIcon className="search-icon" size={28} />
        <input 
          type="text" 
          className="search-input"
          placeholder="Titles, people, genres"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          autoFocus
        />
      </div>

      <div className="filters-container">
        <select 
          className="filter-select"
          value={category}
          onChange={(e) => {
            setSearchParams(prev => {
              if (e.target.value) prev.set('category', e.target.value)
              else prev.delete('category')
              return prev
            })
          }}
        >
          <option value="">All Categories</option>
          <option value="adventure">Adventure</option>
          <option value="learning">Learning</option>
          <option value="maths">Maths</option>
          <option value="science">Science</option>
          <option value="music">Music</option>
          <option value="india">India</option>
        </select>
      </div>

      {(q || category) && (
        <div style={{ marginBottom: '24px', color: 'var(--text-secondary)' }}>
          Explore titles related to: <strong style={{ color: 'white' }}>{q || category}</strong>
        </div>
      )}

      {isLoading && (
        <div className="search-grid">
          {[1,2,3,4].map(i => <div key={i} className="show-card skeleton skeleton-card" />)}
        </div>
      )}

      {!isLoading && (q || category) && results.length === 0 && (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-secondary)' }}>
          <SearchIcon size={48} style={{ opacity: 0.5, marginBottom: '16px' }} />
          <h3>No matches found</h3>
          <p>Try searching for a different title or category</p>
        </div>
      )}

      {!isLoading && results.length > 0 && (
        <div className="search-grid">
          {results.map((show: any) => (
            <Link key={show.slug} to={`/show/${show.slug}`} className="show-card">
              {show.poster_url ? (
                <img src={show.poster_url} alt={show.title} className="show-card-image" />
              ) : (
                <div className="show-card-image" style={{ backgroundColor: '#2a2d38' }} />
              )}
              <div className="show-card-overlay">
                <div className="show-card-title">{show.title}</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
