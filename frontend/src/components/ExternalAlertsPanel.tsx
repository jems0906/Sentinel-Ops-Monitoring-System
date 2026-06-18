import { useMemo, useState } from 'react';
import { ExternalAlertEvent } from '../types';

interface Props {
  alerts: ExternalAlertEvent[];
  onSetAcknowledged: (eventId: number, acknowledged: boolean) => Promise<void>;
}

function severityClass(severity: string): string {
  if (severity === 'critical') return 'down';
  if (severity === 'warning') return 'degraded';
  return 'up';
}

function statusClass(status: string): string {
  if (status === 'firing') return 'down';
  if (status === 'resolved') return 'up';
  return 'degraded';
}

export function ExternalAlertsPanel({ alerts, onSetAcknowledged }: Props) {
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [unacknowledgedOnly, setUnacknowledgedOnly] = useState(false);
  const [autoAckOnly, setAutoAckOnly] = useState(false);
  const [sortByPriority, setSortByPriority] = useState(true);
  const [acknowledgingId, setAcknowledgingId] = useState<number | null>(null);

  const statusOptions = useMemo(() => {
    const values = new Set(alerts.map((alert) => alert.status || 'unknown'));
    return ['all', ...Array.from(values).sort()];
  }, [alerts]);

  const severityOptions = useMemo(() => {
    const values = new Set(alerts.map((alert) => alert.severity || 'unknown'));
    return ['all', ...Array.from(values).sort()];
  }, [alerts]);

  const filteredAlerts = useMemo(() => {
    const severityRank: Record<string, number> = {
      critical: 0,
      warning: 1,
      info: 2,
      unknown: 3,
    };

    const results = alerts.filter((alert) => {
      const statusMatch = statusFilter === 'all' || alert.status === statusFilter;
      const severityMatch = severityFilter === 'all' || alert.severity === severityFilter;
      const unacknowledgedMatch = !unacknowledgedOnly || !alert.acknowledged;
      const autoAckMatch = !autoAckOnly || alert.acknowledged_by === 'auto-rule';
      return statusMatch && severityMatch && unacknowledgedMatch && autoAckMatch;
    });

    if (!sortByPriority) {
      return results;
    }

    return [...results].sort((a, b) => {
      const rankA = severityRank[a.severity] ?? 99;
      const rankB = severityRank[b.severity] ?? 99;
      if (rankA !== rankB) {
        return rankA - rankB;
      }
      return new Date(b.last_seen_at || b.created_at).getTime() - new Date(a.last_seen_at || a.created_at).getTime();
    });
  }, [alerts, statusFilter, severityFilter, sortByPriority, unacknowledgedOnly, autoAckOnly]);

  const hasActiveFilters = statusFilter !== 'all' || severityFilter !== 'all' || unacknowledgedOnly || autoAckOnly;

  function clearFilters() {
    setStatusFilter('all');
    setSeverityFilter('all');
    setUnacknowledgedOnly(false);
    setAutoAckOnly(false);
  }

  async function handleSetAcknowledged(eventId: number, acknowledged: boolean) {
    setAcknowledgingId(eventId);
    try {
      await onSetAcknowledged(eventId, acknowledged);
    } finally {
      setAcknowledgingId(null);
    }
  }

  return (
    <section className="card">
      <h2>External Alerts (Alertmanager)</h2>
      <div className="filter-row">
        <label className="filter-group">
          Status
          <select className="filter-select" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            {statusOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-group">
          Severity
          <select className="filter-select" value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
            {severityOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-check">
          <input
            type="checkbox"
            checked={sortByPriority}
            onChange={(event) => setSortByPriority(event.target.checked)}
          />
          Newest critical first
        </label>
        <button
          type="button"
          className={`chip ${unacknowledgedOnly ? 'active' : ''}`}
          onClick={() => setUnacknowledgedOnly((previous) => !previous)}
        >
          Unacknowledged only
        </button>
        <button
          type="button"
          className={`chip chip-auto ${autoAckOnly ? 'active' : ''}`}
          onClick={() => setAutoAckOnly((previous) => !previous)}
        >
          Auto-ack’d only
        </button>
        <button type="button" onClick={clearFilters} disabled={!hasActiveFilters}>
          Clear filters
        </button>
        <span className="muted">Showing {filteredAlerts.length} of {alerts.length}</span>
      </div>
      <div className="alert-feed compact-feed">
        {alerts.length === 0 && <p>No external alerts received yet.</p>}
        {alerts.length > 0 && filteredAlerts.length === 0 && <p>No alerts match current filters.</p>}
        {filteredAlerts.map((alert) => (
          <article key={alert.id} className="alert-item">
            <div className="alert-meta">
              <span className={`pill ${statusClass(alert.status)}`}>{alert.status}</span>
              <span>{new Date(alert.last_seen_at || alert.created_at).toLocaleString()}</span>
            </div>
            <div className="button-row">
              <span className={`pill ${severityClass(alert.severity)}`}>{alert.severity}</span>
              <span className="pill degraded">{alert.source}</span>
              {alert.repeat_count > 1 && <span className="pill degraded">x{alert.repeat_count}</span>}
              {alert.acknowledged && alert.acknowledged_by !== 'auto-rule' && <span className="pill up">acknowledged</span>}
              {alert.acknowledged && alert.acknowledged_by === 'auto-rule' && <span className="pill up chip-auto-badge">auto-ack’d</span>}
            </div>
            <strong>{alert.alert_name}</strong>
            <p>{alert.summary || 'No summary provided.'}</p>
            <div className="ack-row">
              <span className="muted ack-text">
                {alert.acknowledged
                  ? `${alert.acknowledged_by === 'auto-rule' ? 'Auto-ack’d by rule' : `Acknowledged by ${alert.acknowledged_by || 'ops-user'}`} at ${new Date(alert.acknowledged_at || alert.created_at).toLocaleString()}`
                  : 'Unacknowledged'}
                {alert.repeat_count > 1 ? ` • repeated ${alert.repeat_count} times` : ''}
              </span>
              <button
                type="button"
                onClick={() => handleSetAcknowledged(alert.id, !alert.acknowledged)}
                disabled={acknowledgingId === alert.id}
              >
                {acknowledgingId === alert.id ? 'Saving...' : alert.acknowledged ? 'Unacknowledge' : 'Acknowledge'}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
