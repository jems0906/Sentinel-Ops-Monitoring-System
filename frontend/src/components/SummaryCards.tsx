import { Summary } from '../types';

interface Props {
  summary: Summary | null;
}

type CardMeta = {
  key: keyof Summary;
  label: string;
  colorFn?: (summary: Summary) => 'ok' | 'warn' | 'crit' | null;
  format?: (summary: Summary) => string;
};

const cardMeta: CardMeta[] = [
  {
    key: 'up_targets',
    label: 'Healthy Targets',
    colorFn: (s) => (s.up_targets === s.total_targets && s.total_targets > 0 ? 'ok' : s.up_targets === 0 ? 'crit' : 'warn'),
  },
  {
    key: 'degraded_targets',
    label: 'Degraded Targets',
    colorFn: (s) => (s.degraded_targets === 0 ? null : 'warn'),
  },
  {
    key: 'down_targets',
    label: 'Down Targets',
    colorFn: (s) => (s.down_targets === 0 ? null : 'crit'),
  },
  {
    key: 'open_incidents',
    label: 'Open Incidents',
    colorFn: (s) => (s.open_incidents === 0 ? null : s.open_incidents > 3 ? 'crit' : 'warn'),
  },
  {
    key: 'uptime_percent_24h',
    label: '24h Uptime %',
    colorFn: (s) => (s.uptime_percent_24h >= 99 ? 'ok' : s.uptime_percent_24h >= 95 ? 'warn' : 'crit'),
    format: (s) => `${s.uptime_percent_24h.toFixed(2)}%`,
  },
  {
    key: 'ext_firing',
    label: 'Ext Alerts Firing',
    colorFn: (s) => (s.ext_firing === 0 ? 'ok' : s.ext_firing > 5 ? 'crit' : 'warn'),
  },
  {
    key: 'ext_unacked',
    label: 'Ext Unacknowledged',
    colorFn: (s) => (s.ext_unacked === 0 ? 'ok' : s.ext_unacked > 3 ? 'crit' : 'warn'),
  },
  {
    key: 'ext_auto_acked',
    label: "Ext Auto-Ack\u2019d",
    colorFn: (s) => (s.ext_auto_acked > 0 ? 'warn' : null),
  },
];

export function SummaryCards({ summary }: Props) {
  return (
    <section className="grid cards-grid">
      {cardMeta.map((card) => {
        const color = summary ? (card.colorFn?.(summary) ?? null) : null;
        const display = summary
          ? (card.format ? card.format(summary) : String(summary[card.key]))
          : '...';
        return (
          <article key={card.key} className={`card summary-card${color ? ` summary-card-${color}` : ''}`}>
            <div className="label">{card.label}</div>
            <div className={`value${color ? ` value-${color}` : ''}`}>{display}</div>
          </article>
        );
      })}
    </section>
  );
}
