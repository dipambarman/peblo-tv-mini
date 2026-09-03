import { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { catalogApi } from '../api/catalog'
import { Play } from 'lucide-react'

export default function ShowDetail() {
  const { slug } = useParams<{ slug: string }>()
  const [activeSeason, setActiveSeason] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['catalog'],
    queryFn: () => catalogApi.get(),
  })

  // Find the specific show in the catalog
  const show = useMemo(() => {
    if (!data?.data?.sections) return null
    for (const section of data.data.sections) {
      const found = section.shows.find((s: any) => s.slug === slug)
      if (found) return found
    }
    return null
  }, [data, slug])

  // Set default active season when show loads
  useMemo(() => {
    if (show && activeSeason === null && show.seasons?.length > 0) {
      // Prefer a non-trailer season if available
      const normalSeason = show.seasons.find((s: any) => !s.is_trailer_season)
      setActiveSeason(normalSeason ? normalSeason.season_number : show.seasons[0].season_number)
    }
  }, [show, activeSeason])

  if (isLoading) return (
    <div className="detail-page">
      <div className="skeleton skeleton-hero" style={{ height: '50vh' }} />
      <div className="detail-content">
         <div className="skeleton skeleton-title" />
      </div>
    </div>
  )

  if (!show) return (
    <div style={{ paddingTop: '100px', textAlign: 'center' }}>
      <h2>Show not found</h2>
      <Link to="/" className="btn btn-primary mt-4">Return Home</Link>
    </div>
  )

  const currentSeasonData = show.seasons?.find((s: any) => s.season_number === activeSeason)

  return (
    <div className="detail-page">
      {/* Hero Header */}
      <div className="detail-hero">
        <img 
          src={show.banner_url || show.poster_url} 
          alt={show.title} 
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        />
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', background: 'linear-gradient(0deg, var(--bg-base) 0%, rgba(15, 16, 20, 0.4) 50%, rgba(15, 16, 20, 0.7) 100%)' }} />
      </div>

      <div className="detail-content">
        <div className="detail-header-layout">
          {show.poster_url && (
            <img src={show.poster_url} alt="Poster" className="detail-poster" />
          )}
          <div className="detail-info">
            <h1>{show.title}</h1>
            <div className="detail-meta">
              <span style={{ color: '#10b981', fontWeight: 600 }}>98% Match</span>
              <span>{new Date().getFullYear()}</span>
              <span className="badge-outline">HD</span>
              {show.categories?.slice(0, 3).map((c: string) => (
                <span key={c}>{c}</span>
              ))}
            </div>
            <p className="detail-synopsis">{show.synopsis}</p>
          </div>
        </div>

        {/* Seasons & Episodes */}
        {show.seasons && show.seasons.length > 0 && (
          <div style={{ marginTop: '40px' }}>
            <div className="season-tabs">
              {show.seasons.map((season: any) => (
                <div 
                  key={season.season_number}
                  className={`season-tab ${activeSeason === season.season_number ? 'active' : ''}`}
                  onClick={() => setActiveSeason(season.season_number)}
                >
                  {season.is_trailer_season ? 'Trailers & Extras' : `Season ${season.season_number}`}
                </div>
              ))}
            </div>

            <div className="episode-grid">
              {currentSeasonData?.episodes.map((ep: any) => (
                <div key={ep.content_group} className="episode-row">
                  <div className="episode-number">{ep.episode_number}</div>
                  
                  <div className="episode-thumbnail-container">
                    {ep.thumbnail_url ? (
                      <img src={ep.thumbnail_url} alt={ep.episode_title} className="episode-thumbnail" />
                    ) : (
                      <div className="episode-thumbnail" style={{ background: '#2a2d38' }} />
                    )}
                    <div className="episode-play-overlay">
                      <div className="play-icon">
                        <Play fill="white" size={20} />
                      </div>
                    </div>
                  </div>

                  <div className="episode-details">
                    <div className="episode-header">
                      <div className="episode-title">{ep.episode_title}</div>
                      <div className="episode-duration">
                        {Math.floor(ep.duration_seconds / 60)}m
                      </div>
                    </div>
                    
                    <div className="episode-languages">
                      {ep.languages?.map((lang: string) => (
                        <span key={lang} className="lang-badge">{lang}</span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
