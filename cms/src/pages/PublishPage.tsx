import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { publishApi } from '../api/client'
import { useState } from 'react'

export default function PublishPage() {
  const queryClient = useQueryClient()
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const isAdmin = user.role === 'admin'
  const [publishResult, setPublishResult] = useState<string | null>(null)

  // Validation report
  const { data: reportData, isLoading: reportLoading } = useQuery({
    queryKey: ['validation-report'],
    queryFn: () => publishApi.validationReport(),
  })

  // Publish history
  const { data: historyData } = useQuery({
    queryKey: ['publish-history'],
    queryFn: () => publishApi.history(),
  })

  // Publish mutation
  const publishMutation = useMutation({
    mutationFn: () => publishApi.publish(),
    onSuccess: (res) => {
      setPublishResult(`✅ Published! ${res.data.shows_count} shows, ${res.data.episodes_count} episodes.`)
      queryClient.invalidateQueries({ queryKey: ['publish-history'] })
      queryClient.invalidateQueries({ queryKey: ['validation-report'] })
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { data?: { detail?: string }; status?: number } }
      if (axiosErr.response?.status === 403) {
        setPublishResult('❌ Permission denied. Only admins can publish.')
      } else {
        setPublishResult(`❌ Publish failed: ${axiosErr.response?.data?.detail || 'Unknown error'}`)
      }
    },
  })

  const report = reportData?.data
  const history = historyData?.data || []

  return (
    <div>
      <div className="page-header">
        <h1>Publish Catalogue</h1>
      </div>

      {/* Publish button */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {isAdmin ? (
            <button
              className="btn btn-primary"
              onClick={() => publishMutation.mutate()}
              disabled={publishMutation.isPending}
              style={{ fontSize: 16, padding: '12px 24px' }}
            >
              {publishMutation.isPending ? '⏳ Publishing...' : '🚀 Publish Now'}
            </button>
          ) : (
            <div className="permission-denied" style={{ padding: 16, width: '100%' }}>
              🔒 Only admins can publish. Your role is <strong>{user.role}</strong>.
            </div>
          )}

          {report && (
            <div>
              <strong>{report.summary}</strong>
            </div>
          )}
        </div>

        {!isAdmin && report?.blocking_issues?.length > 0 && (
          <div style={{ marginTop: 12, fontSize: 14, color: 'var(--text-secondary)' }}>
            <strong>Why publish is disabled:</strong>
            <ul style={{ marginTop: 4, paddingLeft: 20 }}>
              {report.blocking_issues.slice(0, 3).map((issue: Record<string, unknown>, i: number) => (
                <li key={i}>{issue.issue as string}</li>
              ))}
              {report.blocking_issues.length > 3 && (
                <li>...and {report.blocking_issues.length - 3} more</li>
              )}
            </ul>
          </div>
        )}

        {publishResult && (
          <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: publishResult.startsWith('✅') ? '#d1fae5' : '#fee2e2' }}>
            {publishResult}
          </div>
        )}
      </div>

      {/* Validation Report */}
      <div className="card">
        <h3 style={{ marginBottom: 16 }}>Validation Report</h3>

        {reportLoading && (
          <div className="loading-spinner"><div className="spinner" /> Loading report...</div>
        )}

        {report && report.blocking_issues?.length === 0 && report.warnings?.length === 0 && (
          <div style={{ textAlign: 'center', padding: 24, color: 'var(--success)' }}>
            ✅ Everything looks good! No issues found.
          </div>
        )}

        {report?.blocking_issues?.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <h4 style={{ color: 'var(--error)', marginBottom: 8 }}>
              ❌ Blocking Issues ({report.blocking_issues.length})
            </h4>
            {report.blocking_issues.map((issue: Record<string, unknown>, i: number) => (
              <div key={i} className="validation-issue error">
                <span className="issue-icon">🚫</span>
                <div className="issue-text">
                  <div className="issue-show">{issue.show as string}</div>
                  {(issue.episode as string) && <div className="issue-episode">{issue.episode as string}</div>}
                  <div>{issue.issue as string}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {report?.warnings?.length > 0 && (
          <div>
            <h4 style={{ color: 'var(--warning)', marginBottom: 8 }}>
              ⚠️ Warnings ({report.warnings.length})
            </h4>
            {report.warnings.map((issue: Record<string, unknown>, i: number) => (
              <div key={i} className="validation-issue warning">
                <span className="issue-icon">⚠️</span>
                <div className="issue-text">
                  <div className="issue-show">{issue.show as string}</div>
                  {(issue.episode as string) && <div className="issue-episode">{issue.episode as string}</div>}
                  <div>{issue.issue as string}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Publish History */}
      <div className="card">
        <h3 style={{ marginBottom: 16 }}>Publish History</h3>

        {history.length === 0 ? (
          <div className="empty-state" style={{ padding: 24 }}>
            <p>No publishes yet.</p>
          </div>
        ) : (
          history.map((run: Record<string, unknown>) => (
            <div key={run.id as string} className="publish-history-item">
              <div className={`run-status ${run.status}`} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500 }}>
                  {run.status === 'success' ? '✅' : run.status === 'failed' ? '❌' : '⏳'}{' '}
                  {new Date(run.started_at as string).toLocaleString()}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  {run.shows_count as number} shows, {run.episodes_count as number} episodes
                  {(run.error_message as string) && ` · Error: ${run.error_message as string}`}
                </div>
              </div>
              <span className={`badge badge-${run.status === 'success' ? 'published' : run.status === 'failed' ? 'error' : 'draft'}`}>
                {run.status as string}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
