import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { episodesApi } from '../api/client'

export default function EpisodeList() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [language, setLanguage] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['episodes', { search, status, language, page }],
    queryFn: () => episodesApi.list({
      page,
      page_size: 50,
      ...(search && { search }),
      ...(status && { status }),
      ...(language && { language }),
    }),
  })

  const episodes = data?.data

  return (
    <div>
      <div className="page-header">
        <h1>Episodes</h1>
      </div>

      <div className="filters-bar">
        <input
          type="text"
          placeholder="Search episodes or show titles..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="">All Status</option>
          <option value="published">Published</option>
          <option value="draft">Draft</option>
        </select>
        <select value={language} onChange={(e) => { setLanguage(e.target.value); setPage(1) }}>
          <option value="">All Languages</option>
          <option value="en">English</option>
          <option value="hi">Hindi</option>
        </select>
      </div>

      {isLoading && (
        <div className="loading-spinner"><div className="spinner" /> Loading episodes...</div>
      )}

      {isError && (
        <div className="card" style={{ color: 'var(--error)' }}>⚠️ Failed to load episodes.</div>
      )}

      {episodes && episodes.items.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <p>No episodes found</p>
        </div>
      )}

      {episodes && episodes.items.length > 0 && (
        <>
          <div className="card table-container">
            <table>
              <thead>
                <tr>
                  <th>Show</th>
                  <th>Season</th>
                  <th>Episode</th>
                  <th>Title</th>
                  <th>Language</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th>Content Group</th>
                </tr>
              </thead>
              <tbody>
                {episodes.items.map((ep: Record<string, unknown>) => (
                  <tr key={ep.id as string}>
                    <td style={{ fontWeight: 500 }}>{ep.show_title as string}</td>
                    <td>S{ep.season_number as number}</td>
                    <td>E{ep.episode_number as number}</td>
                    <td>{ep.episode_title as string}</td>
                    <td>
                      <span className="badge" style={{ background: '#e5e7eb' }}>
                        {(ep.language as string).toUpperCase()}
                      </span>
                    </td>
                    <td>{ep.duration_seconds ? `${Math.floor((ep.duration_seconds as number) / 60)}m ${(ep.duration_seconds as number) % 60}s` : '—'}</td>
                    <td><span className={`badge badge-${ep.status}`}>{ep.status as string}</span></td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {ep.content_group as string}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <span>
              Showing {(page - 1) * 50 + 1}–{Math.min(page * 50, episodes.total)} of {episodes.total}
            </span>
            <div className="pagination-buttons">
              <button className="btn btn-sm btn-secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                ← Previous
              </button>
              <button className="btn btn-sm btn-secondary" disabled={page * 50 >= episodes.total} onClick={() => setPage(p => p + 1)}>
                Next →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
