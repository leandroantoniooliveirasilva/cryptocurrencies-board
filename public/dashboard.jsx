const { useState, useEffect, useMemo } = React;

// Responsive breakpoints
const BREAKPOINTS = {
  mobile: 480,
  tablet: 768,
  desktop: 1024,
};

// Hook to detect mobile viewport
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(window.innerWidth < BREAKPOINTS.tablet);
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < BREAKPOINTS.tablet);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);
  return isMobile;
}

// Simple SVG icon components (replacing lucide-react)
const Icon = ({ children, size = 24, color = 'currentColor', strokeWidth = 2, fill = 'none', ...props }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" {...props}>
    {children}
  </svg>
);

const TrendingUp = (props) => <Icon {...props}><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></Icon>;
const TrendingDown = (props) => <Icon {...props}><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></Icon>;
const Minus = (props) => <Icon {...props}><line x1="5" y1="12" x2="19" y2="12"/></Icon>;
const CheckCircle2 = (props) => <Icon {...props}><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></Icon>;
const Clock = (props) => <Icon {...props}><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></Icon>;
const Eye = (props) => <Icon {...props}><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></Icon>;
const ArrowUpCircle = (props) => <Icon {...props}><circle cx="12" cy="12" r="10"/><polyline points="16 12 12 8 8 12"/><line x1="12" y1="16" x2="12" y2="8"/></Icon>;
const Zap = (props) => <Icon {...props}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></Icon>;
const AlertCircle = (props) => <Icon {...props}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></Icon>;
const Loader2 = (props) => <Icon {...props}><path d="M21 12a9 9 0 1 1-6.219-8.56"/></Icon>;

// Tiered weights by asset type
const WEIGHTS_BY_TYPE = {
  'store-of-value': { institutional: 0.40, supply: 0.25, regulatory: 0.15, wyckoff: 0.15, revenue: 0.05 },
  'smart-contract': { institutional: 0.30, revenue: 0.25, supply: 0.20, regulatory: 0.15, wyckoff: 0.10 },
  'defi': { revenue: 0.35, institutional: 0.25, regulatory: 0.20, supply: 0.15, wyckoff: 0.05 },
  'infrastructure': { institutional: 0.35, regulatory: 0.25, supply: 0.20, revenue: 0.10, wyckoff: 0.10 },
};
const DEFAULT_WEIGHTS = { institutional: 0.30, revenue: 0.20, regulatory: 0.20, supply: 0.20, wyckoff: 0.10 };

function getWeights(assetType) {
  return WEIGHTS_BY_TYPE[assetType] || DEFAULT_WEIGHTS;
}

const PALETTE = {
  bg: '#121110',
  cardBg: '#1a1816',
  cardInset: '#211e1b',
  border: '#3a342d',
  borderStrong: '#55493c',
  textPrimary: '#ede7d9',
  textSecondary: '#a39a8a',
  textMuted: '#958b7b', // Was #6e665a (3.1:1) → now 4.6:1 contrast
  trackBg: '#2a2620',
};

// Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64, 96
const SPACE = {
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 24,
  xl: 32,
  '2xl': 48,
  '3xl': 64,
  '4xl': 96,
};

const DIMENSION_LABELS = {
  institutional: 'Institutional',
  revenue: 'Revenue/Fees',
  regulatory: 'Regulatory',
  supply: 'Supply/On-Chain',
  wyckoff: 'Wyckoff',
};

const ASSET_TYPE_LABELS = {
  'store-of-value': 'Store of Value',
  'smart-contract': 'Smart Contract',
  'defi': 'DeFi',
  'infrastructure': 'Infrastructure',
};

// Tier accents: blue for leaders (positive), teal for runner-ups, gray for observation
const TIER_CONFIG = {
  'leader': { label: 'Leaders', icon: CheckCircle2, accent: '#5aafcf', order: 0 },
  'runner-up': { label: 'Runner-ups', icon: Clock, accent: '#6a9a90', order: 1 },
  'observation': { label: 'Observation', icon: Eye, accent: '#8a8a9a', order: 2 },
};

// Action colors: semantic scale from blue (positive) → neutral → red (negative)
const ACTION_CONFIG = {
  'strong-accumulate': { label: 'Strong Accumulate', desc: 'Dislocation in accumulation zone', bg: '#4ac0e0', fg: '#0a1a20', dot: '#0a1a20', icon: Zap, emphatic: true },
  'accumulate': { label: 'Accumulate', desc: 'Tranche-eligible zone', bg: '#5aafcf', fg: '#0a1820', dot: '#0a1820' },
  'promote': { label: 'Promote Candidate', desc: 'Runner-up earning activation', bg: '#1a3038', fg: '#8ad0e8', dot: '#5aafcf', icon: ArrowUpCircle },
  'hold': { label: 'Hold & Monitor', desc: 'Position active, no action', bg: 'transparent', fg: '#6a9a90', dot: '#6a9a90', border: true },
  'await': { label: 'Await Confirmation', desc: 'Signal building, not yet', bg: 'transparent', fg: '#9a9085', dot: '#9a9085', border: true },
  'observe': { label: 'Observe', desc: 'Scanning only', bg: 'transparent', fg: '#8a8a9a', dot: '#8a8a9a', border: true },
  'stand-aside': { label: 'Stand Aside', desc: 'Do not engage', bg: 'transparent', fg: '#d06868', dot: '#d06868', border: true },
};

function computeComposite(scores, assetType) {
  const weights = getWeights(assetType);
  let total = 0;
  for (const [dim, weight] of Object.entries(weights)) {
    total += (scores[dim] || 50) * weight;
  }
  return Math.round(total);
}

function weeklyDelta(trend) {
  if (!trend || trend.length < 2) return 0;
  const first = trend[0];
  const last = trend[trend.length - 1];
  if (typeof first !== 'number' || typeof last !== 'number' || isNaN(first) || isNaN(last)) return 0;
  return last - first;
}

function monthlyDelta(trend30d) {
  if (!trend30d || trend30d.length < 2) return 0;
  const first = trend30d[0];
  const last = trend30d[trend30d.length - 1];
  if (typeof first !== 'number' || typeof last !== 'number' || isNaN(first) || isNaN(last)) return 0;
  return last - first;
}

function relativeTime(dateStr) {
  if (!dateStr) return null;
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function isStale(dateStr) {
  if (!dateStr) return false;
  const date = new Date(dateStr);
  const now = new Date();
  const diffHours = (now - date) / 3600000;
  return diffHours > 25; // Stale if >25 hours old
}

function Sparkline({ data, accent }) {
  if (!data || data.length < 2) return null;
  // Filter out non-numeric values
  const validData = data.filter(v => typeof v === 'number' && !isNaN(v));
  if (validData.length < 2) return null;
  const min = Math.min(...validData);
  const max = Math.max(...validData);
  const range = max - min || 1;
  const width = 80;
  const height = 24;
  const points = validData.map((v, i) => {
    const x = (i / (validData.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <polyline points={points} fill="none" stroke={accent} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DimensionBar({ label, value, accent, weight }) {
  const safeValue = typeof value === 'number' && !isNaN(value) ? value : 50;
  const displayValue = typeof value === 'number' && !isNaN(value) ? value : '—';
  return (
    <div style={{ marginBottom: `${SPACE.md}px` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: `${SPACE.xs}px`, fontFamily: 'ui-monospace, monospace' }}>
        <span>{label}{weight ? <span style={{ opacity: 0.6, marginLeft: `${SPACE.xs}px` }}>({Math.round(weight * 100)}%)</span> : ''}</span>
        <span style={{ color: PALETTE.textPrimary }}>{displayValue}</span>
      </div>
      <div style={{ height: '3px', background: PALETTE.trackBg, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: '100%',
          background: accent,
          transformOrigin: 'left',
          transform: `scaleX(${safeValue / 100})`,
          transition: 'transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
        }} />
      </div>
    </div>
  );
}

function rsiColor(rsi) {
  if (rsi === null || rsi === undefined) return PALETTE.textMuted;
  if (rsi >= 75) return '#d47878';
  if (rsi >= 70) return '#d49a6a';
  if (rsi <= 25) return '#7aa0c4';
  if (rsi <= 32) return '#8ab0d4';
  return PALETTE.textPrimary;
}

function rsiLabel(rsi) {
  if (rsi === null || rsi === undefined) return 'n/a';
  if (rsi >= 75) return 'Overbought';
  if (rsi >= 70) return 'Elevated';
  if (rsi <= 25) return 'Deep oversold';
  if (rsi <= 32) return 'Oversold';
  return 'Neutral';
}

function RsiRow({ asset }) {
  const { rsi_daily, rsi_weekly } = asset;

  const Cell = ({ label, value }) => (
    <div style={{ flex: 1, textAlign: 'center', padding: `${SPACE.sm}px ${SPACE.sm}px`, background: PALETTE.cardInset }}>
      <div style={{ fontSize: '10px', letterSpacing: '0.1em', textTransform: 'uppercase', color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace', marginBottom: `${SPACE.xs}px` }}>
        {label}
      </div>
      <div style={{ fontFamily: 'Georgia, serif', fontSize: '18px', fontWeight: 400, color: rsiColor(value), lineHeight: 1 }}>
        {value === null || value === undefined ? '—' : value}
      </div>
      <div style={{ fontSize: '10px', color: rsiColor(value), fontFamily: 'ui-monospace, monospace', letterSpacing: '0.05em', marginTop: `${SPACE.xs}px`, fontStyle: 'italic', opacity: 0.85 }}>
        {rsiLabel(value)}
      </div>
    </div>
  );

  return (
    <div style={{ marginBottom: `${SPACE.base}px` }}>
      <div style={{ fontSize: '10px', letterSpacing: '0.1em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: `${SPACE.sm}px`, fontFamily: 'ui-monospace, monospace' }}>
        RSI · 14
      </div>
      <div style={{ display: 'flex', gap: `${SPACE.sm}px` }}>
        <Cell label="Daily" value={rsi_daily} />
        <Cell label="Weekly" value={rsi_weekly} />
      </div>
    </div>
  );
}

function getActionReasoning(asset) {
  const action = asset.action || 'observe';
  const composite = asset.composite || 50;
  const delta = weeklyDelta(asset.trend);
  const rsiDaily = asset.rsi_daily;
  const rsiWeekly = asset.rsi_weekly;
  const tier = asset.tier;

  switch (action) {
    case 'strong-accumulate':
      return `Daily RSI at ${rsiDaily} signals short-term oversold while weekly RSI (${rsiWeekly}) and composite (${composite}) remain healthy. This dislocation within an accumulation zone is a high-conviction entry point.`;
    case 'accumulate':
      return `Composite score of ${composite} with ${delta >= 0 ? 'stable' : 'minor pullback'} trend. RSI levels support accumulation. Leader-tier asset in favorable Wyckoff phase for tranche building.`;
    case 'promote':
      return `Runner-up crossing leader threshold with composite at ${composite}${delta > 0 ? ` and positive ${delta}-point weekly momentum` : ''}. Evaluate for potential tier promotion.`;
    case 'hold':
      return `Position active with composite at ${composite}. No accumulate or trim signals present. Current allocation appropriate — patience is the strategy.`;
    case 'await':
      return `Signal building but not yet confirmed. Composite at ${composite}${delta > 0 ? ` with ${delta}-point uptick` : ''}. Monitor for entry criteria before activation.`;
    case 'observe':
      return `Observation tier — scanning only. ${composite >= 70 ? 'Composite healthy but' : 'Composite at ' + composite + ','} no position warranted at this time.`;
    case 'stand-aside':
      return `Distribution risk detected${delta < -3 ? ` with ${Math.abs(delta)}-point weekly decline` : ''}${rsiWeekly >= 70 ? ` and elevated weekly RSI (${rsiWeekly})` : ''}. Do not engage regardless of price action.`;
    default:
      return null;
  }
}

function ActionBanner({ action, daysAgo, strongDays }) {
  const cfg = ACTION_CONFIG[action];
  if (!cfg) return null;
  const recentChange = daysAgo <= 14;
  const Icon = cfg.icon;
  const isStrong = action === 'strong-accumulate';

  return (
    <div style={{
      background: cfg.bg,
      color: cfg.fg,
      border: cfg.border ? `1px solid ${cfg.dot}` : 'none',
      padding: `${SPACE.md}px ${SPACE.base}px`,
      marginBottom: `${SPACE.base}px`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: `${SPACE.sm}px`,
      boxShadow: isStrong ? `0 0 0 2px ${PALETTE.bg}, 0 0 0 3px #4ac0e0` : 'none',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: `${SPACE.sm}px` }}>
        {Icon ? (
          <Icon size={isStrong ? 16 : 14} color={cfg.dot} strokeWidth={1.75} fill={isStrong ? cfg.dot : 'none'} />
        ) : (
          <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: cfg.dot, flexShrink: 0 }} />
        )}
        <div>
          <div style={{ fontSize: '11px', letterSpacing: '0.12em', textTransform: 'uppercase', fontFamily: 'ui-monospace, monospace', fontWeight: isStrong ? 700 : 500 }}>
            {cfg.label}
          </div>
          <div style={{ fontSize: '10px', letterSpacing: '0.05em', opacity: 0.8, fontFamily: 'ui-monospace, monospace', marginTop: '2px' }}>
            {cfg.desc}
          </div>
        </div>
      </div>
      <div style={{ fontSize: '10px', letterSpacing: '0.08em', fontFamily: 'ui-monospace, monospace', textAlign: 'right', lineHeight: 1.3, opacity: recentChange ? 1 : 0.7 }}>
        {isStrong && strongDays > 1 ? (
          <>
            <div style={{ fontWeight: 600, marginBottom: '1px' }}>DAY {strongDays}</div>
            <div style={{ opacity: 0.7 }}>continuation</div>
          </>
        ) : isStrong && strongDays === 1 ? (
          <>
            <div style={{ fontWeight: 700, marginBottom: '1px' }}>NEW</div>
            <div>today</div>
          </>
        ) : (
          <>
            {recentChange && <div style={{ fontWeight: 600, marginBottom: '1px' }}>NEW</div>}
            <div>{daysAgo || 0}d</div>
          </>
        )}
      </div>
    </div>
  );
}

function ScoreCard({ asset, isMobile }) {
  const [showAllDimensions, setShowAllDimensions] = useState(false);
  const assetType = asset.asset_type || 'smart-contract';
  const weights = asset.weights || getWeights(assetType);
  const composite = asset.composite || computeComposite(asset.scores, assetType);
  const delta = weeklyDelta(asset.trend);
  const config = TIER_CONFIG[asset.tier];
  if (!config) return null;
  const Icon = config.icon;
  const action = asset.action || 'observe';
  const isStrong = action === 'strong-accumulate';

  const deltaColor = delta > 0 ? '#7aa872' : delta < 0 ? '#c27878' : PALETTE.textMuted;
  const DeltaIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;

  // Sort dimensions by weight to show top 3 by default
  const sortedDimensions = Object.entries(weights)
    .sort(([, a], [, b]) => b - a)
    .map(([key]) => key);
  const visibleDimensions = showAllDimensions ? sortedDimensions : sortedDimensions.slice(0, 3);
  const hiddenCount = sortedDimensions.length - 3;

  return (
    <div style={{
      background: PALETTE.cardBg,
      border: isStrong ? `1px solid #4ac0e0` : `1px solid ${PALETTE.borderStrong}`,
      padding: isMobile ? `${SPACE.base}px` : `${SPACE.lg}px`,
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: `${SPACE.base}px` }}>
        <div>
          <div style={{ fontFamily: 'Georgia, serif', fontSize: isMobile ? '22px' : '24px', fontWeight: 400, color: PALETTE.textPrimary, lineHeight: 1 }}>
            {asset.symbol}
          </div>
          <div style={{ fontSize: '10px', letterSpacing: '0.1em', textTransform: 'uppercase', color: PALETTE.textSecondary, marginTop: `${SPACE.xs}px`, fontFamily: 'ui-monospace, monospace' }}>
            {asset.name}
          </div>
          <div style={{ fontSize: '10px', letterSpacing: '0.08em', textTransform: 'uppercase', color: PALETTE.textMuted, marginTop: `${SPACE.xs}px`, fontFamily: 'ui-monospace, monospace' }}>
            {ASSET_TYPE_LABELS[assetType] || assetType}
          </div>
        </div>
        <Icon size={16} color={config.accent} strokeWidth={1.5} />
      </div>

      <ActionBanner action={action} daysAgo={asset.label_changed_days_ago} strongDays={asset.strong_accumulate_days_active} />

      {/* Action reasoning */}
      <div style={{
        fontSize: '11px',
        color: PALETTE.textSecondary,
        fontFamily: 'Georgia, serif',
        fontStyle: 'italic',
        lineHeight: 1.5,
        marginBottom: `${SPACE.lg}px`,
        paddingLeft: `${SPACE.sm}px`,
        borderLeft: `2px solid ${PALETTE.border}`,
      }}>
        {getActionReasoning(asset)}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: `${SPACE.md}px`, marginBottom: `${SPACE.xs}px`, flexWrap: 'wrap' }}>
        <div style={{ fontFamily: 'Georgia, serif', fontSize: isMobile ? '40px' : '48px', fontWeight: 300, color: PALETTE.textPrimary, lineHeight: 1, letterSpacing: '-0.02em' }}>
          {composite}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '3px', color: deltaColor, fontSize: '11px', fontFamily: 'ui-monospace, monospace' }}>
          <DeltaIcon size={11} strokeWidth={2} />
          <span>{delta > 0 ? '+' : ''}{delta}</span>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <Sparkline data={asset.trend} accent={config.accent} />
        </div>
      </div>
      <div style={{ fontSize: '10px', letterSpacing: '0.1em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: `${SPACE.lg}px`, fontFamily: 'ui-monospace, monospace' }}>
        Composite · 7d
      </div>

      <div style={{ marginBottom: `${SPACE.base}px` }}>
        {visibleDimensions.map(dim => (
          <DimensionBar
            key={dim}
            label={DIMENSION_LABELS[dim]}
            value={asset.scores[dim]}
            accent={config.accent}
            weight={weights[dim]}
          />
        ))}
        {hiddenCount > 0 && !showAllDimensions && (
          <button
            onClick={() => setShowAllDimensions(true)}
            style={{
              background: 'transparent',
              border: 'none',
              color: PALETTE.textSecondary,
              fontSize: '10px',
              fontFamily: 'ui-monospace, monospace',
              letterSpacing: '0.08em',
              cursor: 'pointer',
              padding: isMobile ? '12px 0' : '4px 0',
              minHeight: isMobile ? '44px' : 'auto',
              opacity: 0.8,
            }}
          >
            +{hiddenCount} more
          </button>
        )}
        {showAllDimensions && (
          <button
            onClick={() => setShowAllDimensions(false)}
            style={{
              background: 'transparent',
              border: 'none',
              color: PALETTE.textSecondary,
              fontSize: '10px',
              fontFamily: 'ui-monospace, monospace',
              letterSpacing: '0.08em',
              cursor: 'pointer',
              padding: isMobile ? '12px 0' : '4px 0',
              minHeight: isMobile ? '44px' : 'auto',
              opacity: 0.8,
            }}
          >
            Show less
          </button>
        )}
      </div>

      <RsiRow asset={asset} />

      <div style={{ borderTop: `1px solid ${PALETTE.border}`, paddingTop: `${SPACE.md}px`, marginTop: 'auto' }}>
        <div style={{ fontSize: '10px', letterSpacing: '0.1em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: `${SPACE.xs}px`, fontFamily: 'ui-monospace, monospace' }}>
          {asset.wyckoff_phase}
        </div>
        <div style={{ fontSize: '11px', color: PALETTE.textSecondary, fontStyle: 'italic', fontFamily: 'Georgia, serif', lineHeight: 1.5 }}>
          {asset.note}
        </div>
      </div>
    </div>
  );
}

function ActionLegend({ isMobile }) {
  const items = [
    { key: 'strong-accumulate', text: 'Dislocation inside accumulation zone. Daily RSI ≤32, weekly ≥42, composite stable WoW. Shows day-counter when firing consecutively.' },
    { key: 'accumulate', text: 'Tranche-eligible. Leader, composite ≥75, Wyckoff Phase C+, non-negative trend, weekly RSI <75.' },
    { key: 'promote', text: 'Runner-up crossing leader threshold. Composite ≥75 with 30-day trend ≥+8. Manual promotion decision required.' },
    { key: 'hold', text: 'Active position. No add/trim signal. The default state — patience by design.' },
    { key: 'await', text: 'Runner-up building signal. Analytical hold only, no activation yet.' },
    { key: 'observe', text: 'Observation tier. Scanning, not deciding. No position.' },
    { key: 'stand-aside', text: 'Distribution risk or sharp negative trend. Do not engage regardless of price.' },
  ];
  return (
    <details style={{ maxWidth: '1400px', margin: `0 auto ${SPACE.xl}px`, fontSize: '11px', color: PALETTE.textSecondary }}>
      <summary style={{ cursor: 'pointer', fontFamily: 'ui-monospace, monospace', fontSize: '11px', letterSpacing: '0.1em', textTransform: 'uppercase', color: PALETTE.textMuted, display: 'flex', alignItems: 'center', gap: `${SPACE.sm}px`, listStyle: 'none', minHeight: isMobile ? '44px' : 'auto', padding: isMobile ? `${SPACE.sm}px 0` : 0 }}>
        <span style={{ transition: 'transform 0.2s', display: 'inline-block' }}>▸</span>
        Action rules
      </summary>
      <style>{`details[open] summary span:first-child { transform: rotate(90deg); }`}</style>
      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(280px, 1fr))', gap: `${SPACE.base}px`, marginTop: `${SPACE.lg}px` }}>
        {items.map(item => {
          const cfg = ACTION_CONFIG[item.key];
          return (
            <div key={item.key} style={{ display: 'flex', gap: `${SPACE.md}px`, alignItems: 'flex-start' }}>
              <div style={{ width: `${SPACE.sm}px`, height: `${SPACE.sm}px`, borderRadius: '50%', background: cfg.dot === '#121110' ? cfg.bg : cfg.dot, marginTop: '5px', flexShrink: 0 }} />
              <div>
                <div style={{ fontFamily: 'ui-monospace, monospace', fontSize: '10px', letterSpacing: '0.1em', textTransform: 'uppercase', color: PALETTE.textPrimary, marginBottom: `${SPACE.xs}px`, fontWeight: 500 }}>
                  {cfg.label}
                </div>
                <div style={{ fontFamily: 'Georgia, serif', fontStyle: 'italic', lineHeight: 1.5 }}>
                  {item.text}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </details>
  );
}

function LoadingState() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh', gap: '16px' }}>
      <Loader2 size={32} color={PALETTE.textMuted} style={{ animation: 'spin 1s linear infinite' }} />
      <div style={{ fontSize: '12px', color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace' }}>Loading scores...</div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function ErrorState({ error, onRetry }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh', gap: '16px', padding: '24px' }}>
      <AlertCircle size={32} color="#c27878" />
      <div style={{ fontSize: '14px', color: PALETTE.textPrimary, fontFamily: 'Georgia, serif', textAlign: 'center' }}>
        Failed to load scoring data
      </div>
      <div style={{ fontSize: '11px', color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace', textAlign: 'center', maxWidth: '400px' }}>
        {error}
      </div>
      <button
        onClick={onRetry}
        style={{
          background: 'transparent',
          color: PALETTE.textPrimary,
          border: `1px solid ${PALETTE.borderStrong}`,
          padding: '8px 16px',
          fontSize: '11px',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          fontFamily: 'ui-monospace, monospace',
          cursor: 'pointer',
          marginTop: '8px',
        }}
      >
        Retry
      </button>
    </div>
  );
}

function Dashboard() {
  const [assets, setAssets] = useState([]);
  const [generatedAt, setGeneratedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTier, setActiveTier] = useState('all');
  const isMobile = useIsMobile();

  const fetchData = () => {
    setLoading(true);
    setError(null);
    fetch('./latest.json')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        setAssets(data.assets || []);
        setGeneratedAt(data.generated_at);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredAssets = useMemo(() => {
    const sorted = [...assets].sort((a, b) => {
      const aStrong = a.action === 'strong-accumulate' ? 0 : 1;
      const bStrong = b.action === 'strong-accumulate' ? 0 : 1;
      const tierDiff = (TIER_CONFIG[a.tier]?.order || 0) - (TIER_CONFIG[b.tier]?.order || 0);
      if (tierDiff !== 0) return tierDiff;
      if (aStrong !== bStrong) return aStrong - bStrong;
      return (b.composite || 0) - (a.composite || 0);
    });
    if (activeTier === 'all') return sorted;
    return sorted.filter(a => a.tier === activeTier);
  }, [activeTier, assets]);

  const groupedAssets = useMemo(() => {
    const groups = { leader: [], 'runner-up': [], observation: [] };
    filteredAssets.forEach(a => {
      if (groups[a.tier]) groups[a.tier].push(a);
    });
    return groups;
  }, [filteredAssets]);

  const strongCount = assets.filter(a => a.action === 'strong-accumulate').length;

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: PALETTE.bg, fontFamily: 'Georgia, serif', color: PALETTE.textPrimary }}>
        <LoadingState />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: '100vh', background: PALETTE.bg, fontFamily: 'Georgia, serif', color: PALETTE.textPrimary }}>
        <ErrorState error={error} onRetry={fetchData} />
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: PALETTE.bg,
      fontFamily: 'Georgia, serif',
      color: PALETTE.textPrimary,
      padding: isMobile ? `${SPACE.lg}px ${SPACE.base}px` : `${SPACE['2xl']}px ${SPACE.lg}px`,
    }}>
      <div style={{ maxWidth: '1400px', margin: `0 auto ${isMobile ? SPACE.lg : SPACE['2xl']}px`, borderBottom: `1px solid ${PALETTE.borderStrong}`, paddingBottom: `${SPACE.lg}px` }}>
        <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', justifyContent: 'space-between', alignItems: isMobile ? 'stretch' : 'flex-start', gap: `${SPACE.lg}px` }}>
          <div style={{ flex: '1 1 auto' }}>
            <div style={{ fontSize: '10px', letterSpacing: '0.2em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: `${SPACE.sm}px`, fontFamily: 'ui-monospace, monospace' }}>
              Framework · Daily scan
            </div>
            <h1 style={{ fontSize: isMobile ? '26px' : '32px', fontWeight: 400, margin: 0, letterSpacing: '-0.01em', lineHeight: 1.1, color: PALETTE.textPrimary }}>
              Conviction Scores
            </h1>
            <div style={{ fontSize: '12px', color: PALETTE.textSecondary, marginTop: `${SPACE.sm}px`, fontStyle: 'italic' }}>
              5 dimensions · Tiered weights by asset type · RSI confirmation layer
            </div>
            {generatedAt && (
              <div style={{ fontSize: '11px', color: isStale(generatedAt) ? '#d49a6a' : PALETTE.textMuted, marginTop: `${SPACE.sm}px`, fontFamily: 'ui-monospace, monospace', display: 'flex', alignItems: 'center', gap: `${SPACE.sm}px` }}>
                {isStale(generatedAt) && <AlertCircle size={12} color="#d49a6a" strokeWidth={2} />}
                <span>Updated {relativeTime(generatedAt)}{isStale(generatedAt) ? ' · Data may be stale' : ''}</span>
              </div>
            )}
          </div>
          {strongCount > 0 && (
            <div style={{ padding: `${SPACE.md}px ${SPACE.base}px`, background: '#0f2028', border: '1px solid #4ac0e0', display: 'inline-flex', alignItems: 'center', gap: `${SPACE.sm}px`, flexShrink: 0 }}>
              <Zap size={14} color="#4ac0e0" fill="#4ac0e0" strokeWidth={1.75} />
              <span style={{ fontSize: '10px', letterSpacing: '0.12em', textTransform: 'uppercase', color: '#4ac0e0', fontFamily: 'ui-monospace, monospace', fontWeight: 600 }}>
                {strongCount} Strong Accumulate signal{strongCount > 1 ? 's' : ''} active
              </span>
            </div>
          )}
        </div>
      </div>

      <ActionLegend isMobile={isMobile} />

      <div style={{ maxWidth: '1400px', margin: `0 auto ${SPACE.xl}px`, display: 'flex', gap: `${SPACE.sm}px`, flexWrap: 'wrap' }}>
        {[
          { id: 'all', label: 'All' },
          { id: 'leader', label: 'Leaders' },
          { id: 'runner-up', label: 'Runner-ups' },
          { id: 'observation', label: 'Observation' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTier(t.id)}
            style={{
              background: activeTier === t.id ? PALETTE.textPrimary : 'transparent',
              color: activeTier === t.id ? PALETTE.bg : PALETTE.textPrimary,
              border: `1px solid ${PALETTE.borderStrong}`,
              padding: isMobile ? `${SPACE.md}px ${SPACE.base}px` : `${SPACE.sm}px ${SPACE.base}px`,
              minHeight: isMobile ? '44px' : 'auto',
              fontSize: '11px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              fontFamily: 'ui-monospace, monospace',
              cursor: 'pointer',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {['leader', 'runner-up', 'observation'].map(tier => {
          const config = TIER_CONFIG[tier];
          const tierAssets = groupedAssets[tier];
          // Skip tier if no assets and not filtering to this specific tier
          if (tierAssets.length === 0 && activeTier !== tier) return null;

          return (
            <div key={tier} style={{ marginBottom: `${SPACE['3xl']}px` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: `${SPACE.md}px`, marginBottom: `${SPACE.lg}px` }}>
                <div style={{ width: `${SPACE.xl}px`, height: '1px', background: config.accent }} />
                <h2 style={{ fontSize: '11px', letterSpacing: '0.2em', textTransform: 'uppercase', color: config.accent, fontFamily: 'ui-monospace, monospace', fontWeight: 500, margin: 0 }}>
                  {config.label} — {tierAssets.length}
                </h2>
              </div>
              {tierAssets.length === 0 ? (
                <div style={{
                  textAlign: 'center',
                  padding: `${SPACE['2xl']}px ${SPACE.lg}px`,
                  color: PALETTE.textMuted,
                  fontFamily: 'Georgia, serif',
                  fontStyle: 'italic',
                  fontSize: '13px',
                  background: PALETTE.cardBg,
                  border: `1px dashed ${PALETTE.border}`,
                }}>
                  No assets in this tier yet
                </div>
              ) : (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(300px, 1fr))',
                  gap: `${isMobile ? SPACE.base : SPACE.lg}px`,
                }}>
                  {tierAssets.map(asset => (
                    <ScoreCard key={asset.symbol} asset={asset} isMobile={isMobile} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div style={{ maxWidth: '1400px', margin: `${isMobile ? SPACE['2xl'] : SPACE['3xl']}px auto 0`, borderTop: `1px solid ${PALETTE.border}`, paddingTop: `${SPACE.lg}px` }}>
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(240px, 1fr))', gap: `${SPACE.lg}px`, fontSize: '11px', color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace', letterSpacing: '0.04em', lineHeight: 1.6 }}>
          <div>
            <div style={{ color: PALETTE.textSecondary, marginBottom: `${SPACE.xs}px`, fontWeight: 500 }}>Scoring</div>
            Daily conviction framework. Data refreshed at 12:00 UTC.
          </div>
          <div>
            <div style={{ color: PALETTE.textSecondary, marginBottom: `${SPACE.xs}px`, fontWeight: 500 }}>Dimensions</div>
            Institutional · Revenue · Regulatory · Supply · Wyckoff
          </div>
          <div>
            <div style={{ color: PALETTE.textSecondary, marginBottom: `${SPACE.xs}px`, fontWeight: 500 }}>Strong Accumulate</div>
            Fires when leader sees daily RSI flush with weekly + composite intact.
          </div>
        </div>
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<Dashboard />);
