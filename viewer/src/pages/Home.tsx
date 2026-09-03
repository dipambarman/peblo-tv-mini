import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { catalogApi } from '../api/catalog'
import { Play, Info } from 'lucide-react'

export default function Home() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['catalog'],
    queryFn: () => catalogApi.get(),
  })

  if (isLoading) {
    return (
      <div className="home-container">
        <div className="skeleton skeleton-hero" />
        <div className="catalog-section" style={{ padding: '20px 4%' }}>
          <div className="skeleton skeleton-text" style={{ width: '200px' }} />
          <div className="row-scroll">
            {[1,2,3,4,5].map(i => <div key={i} className="show-card skeleton skeleton-card" />)}
          </div>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div style={{ paddingTop: '100px', textAlign: 'center' }}>
        <h2 style={{ color: 'var(--brand-primary)' }}>Catalog Unavailable</h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '16px' }}>
          Please make sure the catalog has been published in the CMS.
        </p>
      </div>
    )
  }

  const catalog = data?.data
  if (!catalog || !catalog.sections) return null

  // Find featured show for hero
  let heroShow = null
  const featuredSection = catalog.sections.find((s: any) => s.section === 'featured')
  if (featuredSection && featuredSection.shows.length > 0) {
    heroShow = featuredSection.shows[0]
  } else if (catalog.sections.length > 0 && catalog.sections[0].shows.length > 0) {
    heroShow = catalog.sections[0].shows[0]
  }

  return (
    <div className="home-container">
      {/* Hero Section */}
      {heroShow && (
        <div className="hero-container">
          <img 
            src={heroShow.banner_url || heroShow.poster_url} 
            alt={heroShow.title} 
            className="hero-image"
          />
          <div className="hero-gradient" />
          <div className="hero-gradient-side" />
          
          <div className="hero-content">
            <h1 className="hero-title">{heroShow.title}</h1>
            
            <div className="hero-metadata">
              <span style={{ color: '#10b981', fontWeight: 600 }}>New</span>
              <span>{heroShow.seasons?.length || 0} Seasons</span>
              <span className="badge-outline">HD</span>
              <span className="badge-outline">{heroShow.categories?.[0]}</span>
            </div>
            
            <p className="hero-synopsis">{heroShow.synopsis}</p>
            
            <div style={{ display: 'flex', gap: '16px' }}>
              <Link to={`/show/${heroShow.slug}`} className="btn btn-primary">
                <Play fill="currentColor" size={24} /> Play
              </Link>
              <Link to={`/show/${heroShow.slug}`} className="btn btn-secondary">
                <Info size={24} /> More Info
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Catalog Sections */}
      <div style={{ marginTop: heroShow ? '-10vw' : '100px', position: 'relative', zIndex: 10 }}>
        {catalog.sections.map((section: any) => (
          <div key={section.section} className="catalog-section" id={section.section}>
            <h2 className="section-title">
              {section.section.charAt(0).toUpperCase() + section.section.slice(1)}
            </h2>
            <div className="row-container">
              <div className="row-scroll">
                {section.shows.map((show: any) => (
                  <Link key={show.slug} to={`/show/${show.slug}`} className="show-card">
                    {show.poster_url ? (
                      <img src={show.poster_url} alt={show.title} className="show-card-image" loading="lazy" />
                    ) : (
                      <div className="show-card-image" style={{ backgroundColor: '#2a2d38', display: 'flex', alignItems: 'center', padding: '20px', textAlign: 'center' }}>
                        {show.title}
                      </div>
                    )}
                    <div className="show-card-overlay">
                      <div className="show-card-title">{show.title}</div>
                      <div style={{ display: 'flex', gap: '8px', marginTop: '4px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                        {show.categories?.slice(0,2).map((c:string) => (
                          <span key={c}>{c}</span>
                        ))}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
      
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>
        Published at {new Date(catalog.published_at).toLocaleString()}
      </div>
    </div>
  )
}
