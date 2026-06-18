import { AlertEvent } from '../types';

interface Props {
  alerts: AlertEvent[];
}

export function AlertsPanel({ alerts }: Props) {
  return (
    <section className="card">
      <h2>Alert Feed</h2>
      <div className="alert-feed">
        {alerts.length === 0 && <p>No alerts emitted yet.</p>}
        {alerts.map((alert) => (
          <article key={alert.id} className="alert-item">
            <div className="alert-meta">
              <span className="pill degraded">{alert.channel}</span>
              <span>{new Date(alert.created_at).toLocaleString()}</span>
            </div>
            <strong>{alert.subject}</strong>
            <p>{alert.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
