import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useRef } from 'react'
import { showsApi, episodesApi, artworkApi } from '../api/client'

const ARTWORK_SPECS: Record<string, { label: string; ratio: string; dims: string }> = {
  poster:    { label: 'Poster',    ratio: '2:3',  dims: '600×900px' },
  banner:    { label: 'Banner',    ratio: '16:9', dims: '1280×720px' },
  thumbnail: { label: 'Thumbnail', ratio: '16:9', dims: '640×360px' },
}

export default function ShowDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()

  const { data: showData, isLoading, isError } = useQuery({
    queryKey: ['show', id],
    queryFn: () => showsApi.get(id!),
    enabled: !!id,
  })

  const { data: episodesData } = useQuery({
    queryKey: ['episodes', { show_id: id }],
    queryFn: () => episodesApi.list({ show_id: id!, page_size: 100 }),
    enabled: !!id,
  })

  const show = showData?.data
  const episodes = episodesData?.data?.items || []

  if (isLoading) return <div className="loading-spinner"><div className="spinner" /> Loading...</div>
  if (isError || !show) return <div className="card" style={{ color: 'var(--error)' }}>⚠️ Show not found</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/shows" style={{ fontSize: 14, color: 'var(--text-secondary)', textDecoration: 'none' }}>← Back to Shows</Link>
          <h1 style={{ marginTop: 8 }}>{show.title}</h1>
          <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
            {show.slug} · {show.section || '❌ No section'} · <span className={`badge badge-${show.status}`}>{show.status}</span>
          </div>
        </div>
      </div>

      {/* Show details card */}
      <div className="card">
        <h3 style={{ marginBottom: 12 }}>Show Details</h3>
        <div className="form-row">
          <div><strong>Synopsis:</strong> {show.synopsis || '—'}</div>
          <div><strong>Categories:</strong> {show.categories?.join(', ') || '—'}</div>
        </div>
      </div>

      {/* Artwork upload */}
      <div className="card">
        <h3 style={{ marginBottom: 4 }}>Artwork</h3>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
          Upload three images. Each must match the required dimensions and be under 200 KB.
        </p>
        <div className="artwork-slots">
          {Object.entries(ARTWORK_SPECS).map(([type, spec]) => (
            <ArtworkSlot
              key={type}
              showId={id!}
              artworkType={type}
              spec={spec}
              existing={show.artworks?.find((a: Record<string, unknown>) => a.artwork_type === type)}
              onSuccess={() => queryClient.invalidateQueries({ queryKey: ['show', id] })}
            />
          ))}
        </div>
      </div>

      {/* Episodes list */}
      <div className="card">
        <h3 style={{ marginBottom: 12 }}>Episodes ({episodes.length})</h3>
        {episodes.length === 0 ? (
          <div className="empty-state" style={{ padding: 24 }}>
            <p>No episodes yet.</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
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
                {episodes.map((ep: Record<string, unknown>) => (
                  <tr key={ep.id as string}>
                    <td>S{ep.season_number as number}</td>
                    <td>E{ep.episode_number as number}</td>
                    <td>{ep.episode_title as string}</td>
                    <td><span className="badge" style={{ background: '#e5e7eb' }}>{(ep.language as string).toUpperCase()}</span></td>
                    <td>{ep.duration_seconds ? `${Math.floor((ep.duration_seconds as number) / 60)}m` : '—'}</td>
                    <td><span className={`badge badge-${ep.status}`}>{ep.status as string}</span></td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{ep.content_group as string}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function ArtworkSlot({ showId, artworkType, spec, existing, onSuccess }: {
  showId: string
  artworkType: string
  spec: { label: string; ratio: string; dims: string }
  existing?: Record<string, unknown>
  onSuccess: () => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  const handleUpload = async (file: File) => {
    setUploading(true)
    setErrors([])
    try {
      await artworkApi.upload(showId, artworkType, file)
      onSuccess()
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: { errors?: string[]; message?: string } | string } } }
      const detail = axiosErr.response?.data?.detail
      if (typeof detail === 'object' && detail?.errors) {
        setErrors(detail.errors)
      } else if (typeof detail === 'string') {
        setErrors([detail])
      } else {
        setErrors(['Upload failed. Please try again.'])
      }
    } finally {
      setUploading(false)
    }
  }

  return (
    <div
      className={`artwork-slot ${existing ? 'has-image' : ''}`}
      onClick={() => fileRef.current?.click()}
    >
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: 'none' }}
        onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
      />

      {existing?.url ? (
        <img src={existing.url as string} alt={spec.label} className="slot-preview" />
      ) : (
        <div style={{ fontSize: 32 }}>🖼️</div>
      )}

      <div className="slot-label">{spec.label}</div>
      <div className="slot-specs">{spec.ratio} · {spec.dims} · max 200 KB</div>

      {uploading && <div style={{ fontSize: 13 }}>Uploading...</div>}

      {existing && (
        <div style={{ fontSize: 12, color: 'var(--success)' }}>
          ✅ {(existing.width as number)}×{(existing.height as number)}px
        </div>
      )}

      {errors.length > 0 && (
        <div className="slot-error">
          {errors.map((err, i) => <div key={i}>⚠️ {err}</div>)}
        </div>
      )}
    </div>
  )
}
