import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { showsApi } from '../api/client'

export default function ShowList() {
  const [search, setSearch] = useState('')
  const [section, setSection] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['shows', { search, section, status, page }],
    queryFn: () => showsApi.list({
      page,
      page_size: 20,
      ...(search && { search }),
      ...(section && { section }),
      ...(status && { status }),
    }),
  })

  const shows = data?.data

  return (
    <div>
      <div className="page-header">
        <h1>Shows</h1>
      </div>

      <div className="filters-bar">
        <input
          type="text"
          placeholder="Search shows..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select value={section} onChange={(e) => { setSection(e.target.value); setPage(1) }}>
          <option value="">All Sections</option>
          <option value="featured">Featured</option>
          <option value="series">Series</option>
          <option value="minisodes">Minisodes</option>
          <option value="songs">Songs</option>
        </select>
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="">All Status</option>
          <option value="published">Published</option>
          <option value="draft">Draft</option>
        </select>
      </div>

      {isLoading && (
        <div className="loading-spinner">
          <div className="spinner" /> Loading shows...
        </div>
      )}

      {isError && (
        <div className="card" style={{ color: 'var(--error)' }}>
          ⚠️ Failed to load shows: {(error as Error).message}
        </div>
      )}

      {shows && shows.items.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">🎬</div>
          <p>No shows found</p>
          {search && <p style={{ fontSize: 14 }}>Try a different search term.</p>}
        </div>
      )}

      {shows && shows.items.length > 0 && (
        <>
          <div className="card table-container">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Section</th>
                  <th>Status</th>
                  <th>Episodes</th>
                  <th>Artwork</th>
                  <th>Categories</th>
                </tr>
              </thead>
              <tbody>
                {shows.items.map((show: Record<string, unknown>) => (
                  <tr key={show.id as string}>
                    <td>
                      <Link to={`/shows/${show.id}`} style={{ color: 'var(--accent)', fontWeight: 600, textDecoration: 'none' }}>
                        {show.title as string}
                      </Link>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{show.slug as string}</div>
                    </td>
                    <td>
                      {show.section
                        ? <span className="badge badge-published">{show.section as string}</span>
                        : <span className="badge badge-error">No section</span>
                      }
                    </td>
                    <td>
                      <span className={`badge badge-${show.status}`}>{show.status as string}</span>
                    </td>
                    <td>{show.episode_count as number}</td>
                    <td>
                      {(show.artworks as Array<unknown>)?.length === 3
                        ? <span style={{ color: 'var(--success)' }}>✅ Complete</span>
                        : <span style={{ color: 'var(--warning)' }}>⚠️ {(show.artworks as Array<unknown>)?.length}/3</span>
                      }
                    </td>
                    <td>
                      {((show.categories as string[]) || []).map((cat: string) => (
                        <span key={cat} className="badge" style={{ background: '#e5e7eb', marginRight: 4 }}>
                          {cat}
                        </span>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <span>
              Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, shows.total)} of {shows.total}
            </span>
            <div className="pagination-buttons">
              <button className="btn btn-sm btn-secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                ← Previous
              </button>
              <button className="btn btn-sm btn-secondary" disabled={page * 20 >= shows.total} onClick={() => setPage(p => p + 1)}>
                Next →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
