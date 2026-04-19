const { useState, useEffect, useMemo, useCallback } = React;

// Responsive breakpoints
const BREAKPOINTS = {
  mobile: 480,
  tablet: 768,
  desktop: 1024,
};

// Default thresholds (overridden by backend config in latest.json)
const DEFAULT_THRESHOLDS = {
  min_display_score: 50,
  stale_hours: 25,
  rsi: {
    overbought: 70,
    oversold: 32,
    capitulation: 30,
  },
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
const X = (props) => <Icon {...props}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></Icon>;
const Info = (props) => <Icon {...props}><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></Icon>;

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

// Type scale: 1.25 ratio, rem-based for accessibility
// Minimum readable size: 12px (0.75rem)
const TYPE = {
  // Sizes
  caption: '0.75rem',    // 12px - minimum for labels
  small: '0.8125rem',    // 13px - secondary text
  body: '0.875rem',      // 14px - body copy
  base: '1rem',          // 16px - emphasized body
  subhead: '1.125rem',   // 18px - subheadings
  heading: '1.5rem',     // 24px - card headings
  title: '2rem',         // 32px - page title
  display: '2.5rem',     // 40px - large numbers (mobile)
  displayLg: '3rem',     // 48px - large numbers (desktop)
  // Line heights
  tight: 1.1,
  snug: 1.25,
  normal: 1.5,
  relaxed: 1.65,
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
  let totalWeight = 0;
  let missingCount = 0;

  for (const [dim, weight] of Object.entries(weights)) {
    const score = scores[dim];
    // Only include dimensions with valid scores
    if (score !== null && score !== undefined && !isNaN(score)) {
      total += score * weight;
      totalWeight += weight;
    } else {
      missingCount += 1;
    }
  }

  // Renormalize if we have any valid scores
  const composite = totalWeight > 0 ? Math.round(total / totalWeight) : 50;
  return { composite, missingCount };
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

function isStale(dateStr, staleHours = 25) {
  if (!dateStr) return false;
  const date = new Date(dateStr);
  const now = new Date();
  const diffHours = (now - date) / 3600000;
  return diffHours > staleHours;
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
  const isMissing = value === null || value === undefined || (typeof value === 'number' && isNaN(value));
  const displayValue = isMissing ? 'N/A' : value;
  const barColor = isMissing ? '#4a4035' : accent;

  return (
    <div style={{ marginBottom: `${SPACE.md}px`, opacity: isMissing ? 0.6 : 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: TYPE.caption, letterSpacing: '0.05em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: `${SPACE.xs}px`, fontFamily: 'ui-monospace, monospace' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {label}
          {weight && !isMissing && <span style={{ opacity: 0.6, marginLeft: `${SPACE.xs}px` }}>({Math.round(weight * 100)}%)</span>}
          {isMissing && <span style={{ opacity: 0.6, marginLeft: `${SPACE.xs}px` }}>(excluded)</span>}
        </span>
        <span style={{
          color: isMissing ? '#d49a6a' : PALETTE.textPrimary,
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}>
          {isMissing && <AlertCircle size={10} color="#d49a6a" strokeWidth={2} />}
          {displayValue}
        </span>
      </div>
      <div style={{ height: '3px', background: PALETTE.trackBg, overflow: 'hidden' }}>
        {isMissing ? (
          <div style={{
            height: '100%',
            width: '100%',
            background: `repeating-linear-gradient(90deg, ${barColor} 0px, ${barColor} 4px, transparent 4px, transparent 8px)`,
          }} />
        ) : (
          <div style={{
            height: '100%',
            width: '100%',
            background: accent,
            transformOrigin: 'left',
            transform: `scaleX(${value / 100})`,
            transition: 'transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
          }} />
        )}
      </div>
    </div>
  );
}

function rsiColor(rsi) {
  if (rsi === null || rsi === undefined) return PALETTE.textMuted;
  if (rsi >= 75) return '#d47878';
  if (rsi >= 70) return '#d49a6a';
  if (rsi < 25) return '#7aa0c4';
  if (rsi <= 32) return '#8ab0d4';
  return PALETTE.textPrimary;
}

function rsiLabel(rsi) {
  if (rsi === null || rsi === undefined) return 'n/a';
  if (rsi >= 75) return 'Overbought';
  if (rsi >= 70) return 'Elevated';
  if (rsi < 25) return 'Deep oversold';
  if (rsi <= 32) return 'Oversold';
  return 'Neutral';
}

function RsiRow({ asset }) {
  const { rsi_daily, rsi_weekly } = asset;

  const Cell = ({ label, value }) => (
    <div style={{ flex: 1, textAlign: 'center', padding: `${SPACE.sm}px ${SPACE.sm}px`, background: PALETTE.cardInset }}>
      <div style={{ fontSize: TYPE.caption, letterSpacing: '0.08em', textTransform: 'uppercase', color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace', marginBottom: `${SPACE.xs}px` }}>
        {label}
      </div>
      <div style={{ fontFamily: 'Georgia, serif', fontSize: TYPE.subhead, fontWeight: 400, color: rsiColor(value), lineHeight: 1 }}>
        {value === null || value === undefined ? '—' : value}
      </div>
      <div style={{ fontSize: TYPE.caption, color: rsiColor(value), fontFamily: 'ui-monospace, monospace', letterSpacing: '0.04em', marginTop: `${SPACE.xs}px`, fontStyle: 'italic', opacity: 0.85 }}>
        {rsiLabel(value)}
      </div>
    </div>
  );

  return (
    <div style={{ marginBottom: `${SPACE.base}px` }}>
      <div style={{ fontSize: TYPE.caption, letterSpacing: '0.08em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: `${SPACE.sm}px`, fontFamily: 'ui-monospace, monospace' }}>
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
  const delta30 = monthlyDelta(asset.trend_30d);
  const rsiDaily = asset.rsi_daily;
  const rsiWeekly = asset.rsi_weekly;

  // Detect if this is a capitulation signal (RSI-driven) vs Wyckoff-driven
  const isCapitulation = rsiWeekly !== null && rsiWeekly < 30;
  const isDeepCapitulation = isCapitulation && rsiDaily !== null && rsiDaily < 30;

  switch (action) {
    case 'strong-accumulate':
      if (isDeepCapitulation) {
        return `Capitulation detected: both daily RSI (${rsiDaily}) and weekly RSI (${rsiWeekly}) below 30. This panic selling in a quality leader is historically a strong entry point. Fundamentals intact at ${composite}.`;
      }
      return `Daily RSI at ${rsiDaily} signals short-term oversold while weekly RSI (${rsiWeekly}) and composite (${composite}) remain healthy. This dislocation within an accumulation zone is a high-conviction entry point.`;
    case 'accumulate':
      if (isCapitulation) {
        return `Weekly RSI at ${rsiWeekly} signals capitulation-level oversold. Quality leaders typically recover from panic selling. Consider measured accumulation while fundamentals remain intact (composite ${composite}).`;
      }
      return `Composite score of ${composite} with ${delta >= 0 ? 'stable' : 'minor pullback'} trend. RSI levels support accumulation. Leader-tier asset in favorable Wyckoff phase for tranche building.`;
    case 'promote':
      return `Runner-up crossing leader threshold with composite at ${composite}${delta30 > 0 ? ` and +${delta30}-point 30-day momentum` : ''}. Evaluate for potential tier promotion.`;
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

function DetailModal({ asset, onClose, isMobile }) {
  // Handle ESC key to close
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  const config = TIER_CONFIG[asset.tier];
  const TierIcon = config?.icon || Eye;
  const assetType = asset.asset_type || 'smart-contract';
  const weights = asset.weights || getWeights(assetType);
  const action = asset.action || 'observe';
  const cfg = ACTION_CONFIG[action];
  const delta = weeklyDelta(asset.trend);
  const deltaColor = delta > 0 ? '#7aa872' : delta < 0 ? '#c27878' : PALETTE.textMuted;
  const DeltaIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;

  // Compute missing dimensions
  let missingDimensions = asset.missing_dimensions || 0;
  if (missingDimensions === 0 && asset.scores) {
    missingDimensions = Object.values(asset.scores).filter(v => v === null || v === undefined).length;
  }
  const hasIncompleteData = missingDimensions > 0;

  // Sort dimensions by weight
  const sortedDimensions = Object.entries(weights)
    .sort(([, a], [, b]) => b - a)
    .map(([key]) => key);

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: isMobile ? SPACE.base : SPACE.xl,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: PALETTE.cardBg,
          border: `1px solid ${PALETTE.borderStrong}`,
          maxWidth: '560px',
          width: '100%',
          maxHeight: '90vh',
          overflow: 'auto',
          position: 'relative',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          padding: isMobile ? SPACE.base : SPACE.lg,
          borderBottom: `1px solid ${PALETTE.border}`,
          position: 'sticky',
          top: 0,
          background: PALETTE.cardBg,
          zIndex: 1,
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
              <span style={{ fontFamily: 'Georgia, serif', fontSize: TYPE.heading, fontWeight: 400, color: PALETTE.textPrimary }}>
                {asset.symbol}
              </span>
              <TierIcon size={14} color={config?.accent || PALETTE.textMuted} strokeWidth={1.5} />
            </div>
            <div style={{ fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, marginTop: SPACE.xs, fontFamily: 'ui-monospace, monospace' }}>
              {asset.name} · {ASSET_TYPE_LABELS[assetType] || assetType}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: PALETTE.textMuted,
              cursor: 'pointer',
              padding: SPACE.sm,
              marginRight: -SPACE.sm,
              marginTop: -SPACE.xs,
              minWidth: 44,
              minHeight: 44,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            aria-label="Close"
          >
            <X size={20} strokeWidth={1.5} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: isMobile ? SPACE.base : SPACE.lg }}>
          {/* Action banner */}
          <div style={{
            background: cfg?.bg || 'transparent',
            border: cfg?.border ? `1px solid ${cfg.dot}` : 'none',
            padding: `${SPACE.md}px ${SPACE.base}px`,
            marginBottom: SPACE.lg,
            display: 'flex',
            alignItems: 'center',
            gap: SPACE.sm,
          }}>
            {cfg?.icon ? (
              <cfg.icon size={16} color={cfg.dot} strokeWidth={1.75} fill={action === 'strong-accumulate' ? cfg.dot : 'none'} />
            ) : (
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: cfg?.dot || PALETTE.textMuted }} />
            )}
            <div>
              <div style={{ fontSize: TYPE.small, letterSpacing: '0.08em', textTransform: 'uppercase', fontFamily: 'ui-monospace, monospace', fontWeight: 600, color: cfg?.fg || PALETTE.textPrimary }}>
                {cfg?.label}
              </div>
              <div style={{ fontSize: TYPE.caption, color: cfg?.fg || PALETTE.textSecondary, opacity: 0.8, fontFamily: 'ui-monospace, monospace', marginTop: 2 }}>
                {cfg?.desc}
              </div>
            </div>
          </div>

          {/* Action reasoning */}
          <div style={{
            fontSize: TYPE.small,
            color: PALETTE.textSecondary,
            fontFamily: 'Georgia, serif',
            fontStyle: 'italic',
            lineHeight: TYPE.normal,
            marginBottom: SPACE.xl,
          }}>
            {getActionReasoning(asset)}
          </div>

          {/* Score section */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: SPACE.md, marginBottom: SPACE.xs }}>
            <div style={{ fontFamily: 'Georgia, serif', fontSize: TYPE.display, fontWeight: 300, color: PALETTE.textPrimary, lineHeight: 1, letterSpacing: '-0.02em' }}>
              {asset.composite}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '3px', color: deltaColor, fontSize: TYPE.small, fontFamily: 'ui-monospace, monospace' }}>
              <DeltaIcon size={12} strokeWidth={2} />
              <span>{delta > 0 ? '+' : ''}{delta}</span>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <Sparkline data={asset.trend} accent={config?.accent} />
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm, fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: SPACE.lg, fontFamily: 'ui-monospace, monospace' }}>
            <span>Composite · 7d trend</span>
            {hasIncompleteData && (
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '3px',
                padding: '2px 6px',
                background: '#3d2a1a',
                border: '1px solid #d49a6a',
                color: '#d49a6a',
                fontSize: TYPE.caption,
              }}>
                <AlertCircle size={10} color="#d49a6a" strokeWidth={2} />
                {missingDimensions} missing
              </span>
            )}
          </div>

          {/* Dimension bars */}
          <div style={{ marginBottom: SPACE.lg }}>
            {sortedDimensions.map(dim => (
              <DimensionBar
                key={dim}
                label={DIMENSION_LABELS[dim]}
                value={asset.scores?.[dim]}
                accent={config?.accent}
                weight={weights[dim]}
              />
            ))}
          </div>

          {/* RSI */}
          <RsiRow asset={asset} />

          {/* Wyckoff phase */}
          <div style={{ marginTop: SPACE.lg, paddingTop: SPACE.md, borderTop: `1px solid ${PALETTE.border}` }}>
            <div style={{ fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: SPACE.xs, fontFamily: 'ui-monospace, monospace' }}>
              {asset.wyckoff_phase}
            </div>
            {asset.note && (
              <div style={{ fontSize: TYPE.small, color: PALETTE.textSecondary, fontStyle: 'italic', fontFamily: 'Georgia, serif', lineHeight: TYPE.normal }}>
                {asset.note}
              </div>
            )}
          </div>

          {/* Detailed analysis if available */}
          {asset.note_detailed && (
            <div style={{ marginTop: SPACE.lg, paddingTop: SPACE.md, borderTop: `1px solid ${PALETTE.border}` }}>
              <div style={{ fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: SPACE.sm, fontFamily: 'ui-monospace, monospace' }}>
                Analysis
              </div>
              <div style={{
                fontFamily: 'Georgia, serif',
                fontSize: TYPE.small,
                lineHeight: TYPE.relaxed,
                color: PALETTE.textSecondary,
                whiteSpace: 'pre-wrap',
              }}>
                {asset.note_detailed}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
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
          <div style={{ fontSize: TYPE.small, letterSpacing: '0.1em', textTransform: 'uppercase', fontFamily: 'ui-monospace, monospace', fontWeight: isStrong ? 700 : 500 }}>
            {cfg.label}
          </div>
          <div style={{ fontSize: TYPE.caption, letterSpacing: '0.04em', opacity: 0.8, fontFamily: 'ui-monospace, monospace', marginTop: '2px' }}>
            {cfg.desc}
          </div>
        </div>
      </div>
      <div style={{ fontSize: TYPE.caption, letterSpacing: '0.06em', fontFamily: 'ui-monospace, monospace', textAlign: 'right', lineHeight: 1.3, opacity: recentChange ? 1 : 0.7 }}>
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
  const [showDetail, setShowDetail] = useState(false);
  const assetType = asset.asset_type || 'smart-contract';

  // Memoize onClose to prevent DetailModal useEffect from re-running on every render
  const handleCloseModal = useCallback((e) => {
    e?.stopPropagation();
    setShowDetail(false);
  }, []);

  // Use pre-computed values if available, otherwise compute
  let composite;
  if (asset.composite !== undefined) {
    composite = asset.composite;
  } else {
    const computed = computeComposite(asset.scores, assetType);
    composite = computed.composite;
  }

  const delta = weeklyDelta(asset.trend);
  const config = TIER_CONFIG[asset.tier];
  if (!config) return null;
  const action = asset.action || 'observe';
  const isStrong = action === 'strong-accumulate';
  const cfg = ACTION_CONFIG[action];

  const deltaColor = delta > 0 ? '#7aa872' : delta < 0 ? '#c27878' : PALETTE.textMuted;
  const DeltaIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;

  return (
    <div
      onClick={() => setShowDetail(true)}
      style={{
        background: PALETTE.cardBg,
        border: isStrong ? `1px solid #4ac0e0` : `1px solid ${PALETTE.border}`,
        padding: isMobile ? `${SPACE.base}px` : `${SPACE.lg}px`,
        display: 'flex',
        flexDirection: 'column',
        cursor: 'pointer',
        transition: 'border-color 0.15s ease',
      }}
      onMouseEnter={(e) => { if (!isStrong) e.currentTarget.style.borderColor = PALETTE.borderStrong; }}
      onMouseLeave={(e) => { if (!isStrong) e.currentTarget.style.borderColor = PALETTE.border; }}
    >
      {/* Header: Symbol + Action badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: SPACE.md }}>
        <div>
          <div style={{ fontFamily: 'Georgia, serif', fontSize: isMobile ? TYPE.subhead : TYPE.heading, fontWeight: 400, color: PALETTE.textPrimary, lineHeight: 1 }}>
            {asset.symbol}
          </div>
          <div style={{ fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, marginTop: SPACE.xs, fontFamily: 'ui-monospace, monospace' }}>
            {asset.name}
          </div>
        </div>
        {/* Compact action badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: SPACE.xs,
          padding: `${SPACE.xs}px ${SPACE.sm}px`,
          background: cfg?.bg || 'transparent',
          border: cfg?.border ? `1px solid ${cfg.dot}` : 'none',
          color: cfg?.fg || PALETTE.textMuted,
        }}>
          {cfg?.icon ? (
            <cfg.icon size={12} color={cfg.dot} strokeWidth={2} fill={isStrong ? cfg.dot : 'none'} />
          ) : (
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: cfg?.dot || PALETTE.textMuted }} />
          )}
          <span style={{ fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'ui-monospace, monospace', fontWeight: isStrong ? 700 : 500 }}>
            {isStrong && asset.strong_accumulate_days_active > 1 ? `Day ${asset.strong_accumulate_days_active}` : cfg?.label?.split(' ')[0] || action}
          </span>
        </div>
      </div>

      {/* Score + Delta */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: SPACE.md, marginTop: 'auto' }}>
        <div style={{ fontFamily: 'Georgia, serif', fontSize: isMobile ? TYPE.title : TYPE.display, fontWeight: 300, color: PALETTE.textPrimary, lineHeight: 1, letterSpacing: '-0.02em' }}>
          {composite}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '3px', color: deltaColor, fontSize: TYPE.small, fontFamily: 'ui-monospace, monospace' }}>
          <DeltaIcon size={12} strokeWidth={2} />
          <span>{delta > 0 ? '+' : ''}{delta}</span>
        </div>
      </div>

      {showDetail && (
        <DetailModal
          asset={asset}
          onClose={handleCloseModal}
          isMobile={isMobile}
        />
      )}
    </div>
  );
}

function ActionSummary({ assets, isMobile, minScore = 50, strongCount = 0, gli = null }) {
  // Get actionable items (not hold, await, observe) with score above threshold
  const actionableStates = ['strong-accumulate', 'accumulate', 'stand-aside', 'promote'];
  const actionableAssets = assets.filter(a =>
    actionableStates.includes(a.action) && (a.composite || 0) >= minScore
  );

  // Group by action type
  const grouped = actionableAssets.reduce((acc, asset) => {
    const action = asset.action;
    if (!acc[action]) acc[action] = [];
    acc[action].push(asset);
    return acc;
  }, {});

  // Order: strong-accumulate first, then accumulate, then promote, then stand-aside
  const orderedActions = ['strong-accumulate', 'accumulate', 'promote', 'stand-aside'];

  const hasActions = actionableAssets.length > 0;
  const showGliWarning = gli && gli.enabled && gli.downtrend && gli.source !== 'fallback';

  // If no actions and no GLI warning, show nothing
  if (!hasActions && !showGliWarning) return null;

  return (
    <div style={{
      maxWidth: '1400px',
      margin: `0 auto ${SPACE.lg}px`,
      display: 'flex',
      flexDirection: 'column',
      gap: `${SPACE.sm}px`,
    }}>
      {/* GLI warning banner when contracting */}
      {showGliWarning && (
        <div style={{
          padding: `${SPACE.sm}px ${SPACE.md}px`,
          background: 'rgba(212, 154, 106, 0.1)',
          border: '1px solid #d49a6a',
          fontSize: TYPE.small,
          color: '#d49a6a',
          fontFamily: 'ui-monospace, monospace',
          display: 'flex',
          alignItems: 'center',
          gap: `${SPACE.sm}px`,
        }}>
          <Info size={14} strokeWidth={1.5} />
          <span>GLI contracting — strong-accumulate signals downgraded</span>
        </div>
      )}

      {/* Action rows */}
      {orderedActions.map(action => {
        const items = grouped[action];
        if (!items || items.length === 0) return null;
        const cfg = ACTION_CONFIG[action];
        const ActionIcon = cfg.icon;
        const isStrong = action === 'strong-accumulate';

        return (
          <div
            key={action}
            style={{
              display: 'flex',
              alignItems: isMobile ? 'flex-start' : 'center',
              flexDirection: isMobile ? 'column' : 'row',
              gap: isMobile ? SPACE.xs : SPACE.md,
              padding: `${SPACE.sm}px ${SPACE.md}px`,
              background: cfg.bg || 'transparent',
              border: cfg.border ? `1px solid ${cfg.dot}` : isStrong ? `1px solid #4ac0e0` : `1px solid ${PALETTE.border}`,
            }}
          >
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: SPACE.sm,
              minWidth: isMobile ? 'auto' : '160px',
            }}>
              {ActionIcon ? (
                <ActionIcon size={14} color={cfg.dot} strokeWidth={1.75} fill={isStrong ? cfg.dot : 'none'} />
              ) : (
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: cfg.dot }} />
              )}
              <span style={{
                fontSize: TYPE.caption,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                fontFamily: 'ui-monospace, monospace',
                fontWeight: 600,
                color: cfg.fg,
              }}>
                {cfg.label}
              </span>
            </div>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: SPACE.sm,
              flex: 1,
            }}>
              {items.map(asset => {
                // Different styling for light vs dark backgrounds
                const isLightBg = action === 'strong-accumulate' || action === 'accumulate';

                return (
                <span
                  key={asset.symbol}
                  style={{
                    fontSize: TYPE.body,
                    fontFamily: 'Georgia, serif',
                    fontWeight: 500,
                    color: isLightBg ? '#fff' : PALETTE.textPrimary,
                    padding: `3px ${SPACE.md}px`,
                    background: isLightBg ? 'rgba(0,0,0,0.35)' : PALETTE.cardInset,
                    borderRadius: '2px',
                    letterSpacing: '0.01em',
                  }}
                >
                  {asset.symbol}
                  <span style={{
                    opacity: 0.75,
                    marginLeft: 6,
                    fontSize: TYPE.small,
                    fontWeight: 400,
                  }}>
                    {asset.composite}
                  </span>
                </span>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StrategySection({ isMobile }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{ marginBottom: `${SPACE.xl}px` }}>
      {/* Summary - always visible */}
      <div style={{
        fontSize: TYPE.body,
        color: PALETTE.textSecondary,
        fontFamily: 'Georgia, serif',
        lineHeight: TYPE.relaxed,
        marginBottom: `${SPACE.md}px`,
      }}>
        A conviction scoring system for patient accumulation. Scores assets across five dimensions to identify <em>what</em> to buy based on fundamentals, uses RSI and Wyckoff analysis to determine <em>when</em> to buy based on technicals.
      </div>

      {/* Expand/collapse button */}
      <button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        style={{
          background: 'transparent',
          border: `1px solid ${PALETTE.border}`,
          color: PALETTE.textMuted,
          padding: `${SPACE.sm}px ${SPACE.md}px`,
          fontSize: TYPE.caption,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          fontFamily: 'ui-monospace, monospace',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: `${SPACE.sm}px`,
          minHeight: isMobile ? '44px' : 'auto',
        }}
      >
        <span style={{
          transition: 'transform 0.2s',
          display: 'inline-block',
          transform: expanded ? 'rotate(90deg)' : 'none',
        }}>▸</span>
        {expanded ? 'Hide details' : 'View strategy details'}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div style={{
          marginTop: `${SPACE.lg}px`,
          padding: `${SPACE.lg}px`,
          background: PALETTE.cardBg,
          border: `1px solid ${PALETTE.border}`,
        }}>
          {/* Philosophy */}
          <div style={{ marginBottom: `${SPACE.xl}px` }}>
            <h3 style={{
              fontSize: TYPE.small,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: PALETTE.textSecondary,
              fontFamily: 'ui-monospace, monospace',
              fontWeight: 500,
              margin: `0 0 ${SPACE.md}px`,
            }}>
              Philosophy
            </h3>
            <div style={{
              fontSize: TYPE.body,
              color: PALETTE.textSecondary,
              fontFamily: 'Georgia, serif',
              lineHeight: TYPE.relaxed,
            }}>
              <p style={{ margin: `0 0 ${SPACE.sm}px` }}>
                <strong style={{ color: PALETTE.textPrimary }}>Leaders go up over time</strong> due to strong fundamentals — institutional adoption, sustainable revenue, regulatory clarity, healthy supply dynamics.
              </p>
              <p style={{ margin: `0 0 ${SPACE.sm}px` }}>
                <strong style={{ color: PALETTE.textPrimary }}>Buying weakness in leaders = mean reversion.</strong> Quality assets recover from panic selling and technical dislocations.
              </p>
              <p style={{ margin: 0 }}>
                <strong style={{ color: PALETTE.textPrimary }}>Buying weakness in non-leaders = momentum trap.</strong> Without fundamental strength, oversold assets often continue declining.
              </p>
            </div>
          </div>

          {/* Dimensions */}
          <div style={{ marginBottom: `${SPACE.xl}px` }}>
            <h3 style={{
              fontSize: TYPE.small,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: PALETTE.textSecondary,
              fontFamily: 'ui-monospace, monospace',
              fontWeight: 500,
              margin: `0 0 ${SPACE.md}px`,
            }}>
              Scoring Dimensions
            </h3>
            <div style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: `${SPACE.md}px`,
              fontSize: TYPE.small,
              color: PALETTE.textMuted,
              fontFamily: 'ui-monospace, monospace',
            }}>
              <div><span style={{ color: PALETTE.textSecondary }}>Institutional</span> — ETF flows, fund holdings, custody</div>
              <div><span style={{ color: PALETTE.textSecondary }}>Revenue</span> — Protocol fees, sustainability</div>
              <div><span style={{ color: PALETTE.textSecondary }}>Regulatory</span> — Jurisdictional clarity</div>
              <div><span style={{ color: PALETTE.textSecondary }}>Supply</span> — Exchange reserves, distribution</div>
              <div><span style={{ color: PALETTE.textSecondary }}>Wyckoff</span> — Technical phase analysis</div>
            </div>
          </div>

          {/* Tiers */}
          <div style={{ marginBottom: `${SPACE.xl}px` }}>
            <h3 style={{
              fontSize: TYPE.small,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: PALETTE.textSecondary,
              fontFamily: 'ui-monospace, monospace',
              fontWeight: 500,
              margin: `0 0 ${SPACE.md}px`,
            }}>
              Asset Tiers
            </h3>
            <div style={{
              fontSize: TYPE.small,
              color: PALETTE.textMuted,
              fontFamily: 'ui-monospace, monospace',
              lineHeight: TYPE.relaxed,
            }}>
              <div style={{ marginBottom: `${SPACE.sm}px` }}>
                <span style={{ color: TIER_CONFIG['leader'].accent }}>Leaders</span> — Core positions for accumulation. Composite ≥75 consistently, clear institutional path, no existential regulatory risk.
              </div>
              <div style={{ marginBottom: `${SPACE.sm}px` }}>
                <span style={{ color: TIER_CONFIG['runner-up'].accent }}>Runner-ups</span> — Promotion candidates. Strong in 2-3 dimensions, improving trajectory toward leader status.
              </div>
              <div>
                <span style={{ color: TIER_CONFIG['observation'].accent }}>Observation</span> — Watch only. Interesting but gaps exist. No position warranted.
              </div>
            </div>
          </div>

          {/* Signal Logic */}
          <div style={{ marginBottom: `${SPACE.xl}px` }}>
            <h3 style={{
              fontSize: TYPE.small,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: PALETTE.textSecondary,
              fontFamily: 'ui-monospace, monospace',
              fontWeight: 500,
              margin: `0 0 ${SPACE.md}px`,
            }}>
              Strong Accumulate Logic
            </h3>
            <div style={{
              fontSize: TYPE.small,
              color: PALETTE.textMuted,
              fontFamily: 'ui-monospace, monospace',
              lineHeight: TYPE.relaxed,
            }}>
              <p style={{ margin: `0 0 ${SPACE.sm}px`, color: PALETTE.textSecondary }}>
                Fires ~5-15 times per year across the watchlist. Two paths:
              </p>
              <div style={{ marginBottom: `${SPACE.sm}px`, paddingLeft: `${SPACE.md}px`, borderLeft: `2px solid ${ACTION_CONFIG['strong-accumulate'].bg}` }}>
                <div style={{ color: PALETTE.textSecondary, marginBottom: '2px' }}>Capitulation</div>
                Weekly RSI &lt;30 AND daily RSI &lt;30. Panic selling in quality leaders. 82.9% hit rate at 30 days.
              </div>
              <div style={{ paddingLeft: `${SPACE.md}px`, borderLeft: `2px solid ${ACTION_CONFIG['strong-accumulate'].bg}` }}>
                <div style={{ color: PALETTE.textSecondary, marginBottom: '2px' }}>Wyckoff Dip</div>
                Phase C + daily RSI ≤32 + weekly RSI ≥42 (stable) + composite ≥75. Short-term flush within healthy structure.
              </div>
              <p style={{ margin: `${SPACE.md}px 0 0`, fontStyle: 'italic' }}>
                Filtered when: GLI contracting, or weekly RSI falling from elevated levels (&gt;55, dropped &gt;8 points).
              </p>
            </div>
          </div>

          {/* Principles */}
          <div>
            <h3 style={{
              fontSize: TYPE.small,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: PALETTE.textSecondary,
              fontFamily: 'ui-monospace, monospace',
              fontWeight: 500,
              margin: `0 0 ${SPACE.md}px`,
            }}>
              Design Principles
            </h3>
            <div style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: `${SPACE.sm}px`,
              fontSize: TYPE.small,
              color: PALETTE.textMuted,
              fontFamily: 'ui-monospace, monospace',
            }}>
              <div><span style={{ color: PALETTE.textSecondary }}>Deliberate</span> — Daily rhythm, not real-time</div>
              <div><span style={{ color: PALETTE.textSecondary }}>Patient</span> — Hold is the default state</div>
              <div><span style={{ color: PALETTE.textSecondary }}>Rare signals</span> — Quality over frequency</div>
              <div><span style={{ color: PALETTE.textSecondary }}>Framework-driven</span> — Prevents emotional drift</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ActionLegend({ isMobile }) {
  const items = [
    { key: 'strong-accumulate', text: 'Capitulation (weekly + daily RSI <30) or Wyckoff dislocation (Phase C+, daily RSI ≤32, composite ≥75).' },
    { key: 'accumulate', text: 'Weekly RSI <30 capitulation, or composite ≥75 in Phase C+ with stable trend.' },
    { key: 'promote', text: 'Runner-up crossing leader threshold. Composite ≥75 with 30-day trend ≥+8.' },
    { key: 'hold', text: 'Active position. No signal. Patience by design.' },
    { key: 'await', text: 'Runner-up building signal. Not yet activated.' },
    { key: 'observe', text: 'Observation tier. Scanning only.' },
    { key: 'stand-aside', text: 'Distribution risk. Do not engage.' },
  ];
  return (
    <details style={{ fontSize: TYPE.small, color: PALETTE.textSecondary }}>
      <summary style={{ cursor: 'pointer', fontFamily: 'ui-monospace, monospace', fontSize: TYPE.small, letterSpacing: '0.08em', textTransform: 'uppercase', color: PALETTE.textMuted, display: 'flex', alignItems: 'center', gap: `${SPACE.sm}px`, listStyle: 'none', minHeight: isMobile ? '44px' : 'auto', padding: isMobile ? `${SPACE.sm}px 0` : 0 }}>
        <span style={{ transition: 'transform 0.2s', display: 'inline-block' }}>▸</span>
        Signal reference
      </summary>
      <style>{`details[open] summary span:first-child { transform: rotate(90deg); }`}</style>
      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(280px, 1fr))', gap: `${SPACE.base}px`, marginTop: `${SPACE.md}px` }}>
        {items.map(item => {
          const cfg = ACTION_CONFIG[item.key];
          return (
            <div key={item.key} style={{ display: 'flex', gap: `${SPACE.sm}px`, alignItems: 'flex-start' }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: cfg.dot === '#121110' ? cfg.bg : cfg.dot, marginTop: '6px', flexShrink: 0 }} />
              <div>
                <span style={{ fontFamily: 'ui-monospace, monospace', fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textSecondary, fontWeight: 500 }}>
                  {cfg.label}
                </span>
                <span style={{ color: PALETTE.textMuted }}> — {item.text}</span>
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
      <div style={{ fontSize: TYPE.small, color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace' }}>Loading scores...</div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function ErrorState({ error, onRetry }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh', gap: '16px', padding: '24px' }}>
      <AlertCircle size={32} color="#c27878" />
      <div style={{ fontSize: TYPE.body, color: PALETTE.textPrimary, fontFamily: 'Georgia, serif', textAlign: 'center' }}>
        Failed to load scoring data
      </div>
      <div style={{ fontSize: TYPE.small, color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace', textAlign: 'center', maxWidth: '400px' }}>
        {error}
      </div>
      <button
        onClick={onRetry}
        style={{
          background: 'transparent',
          color: PALETTE.textPrimary,
          border: `1px solid ${PALETTE.borderStrong}`,
          padding: '8px 16px',
          fontSize: TYPE.small,
          letterSpacing: '0.06em',
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
  const [thresholds, setThresholds] = useState(DEFAULT_THRESHOLDS);
  const [gli, setGli] = useState(null); // Global Liquidity Index status
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTier, setActiveTier] = useState('all');
  const isMobile = useIsMobile();

  const fetchData = () => {
    setLoading(true);
    setError(null);
    // Cache bust with timestamp to avoid stale data
    fetch(`./latest.json?t=${Date.now()}`, { cache: 'no-store' })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        setAssets(data.assets || []);
        setGeneratedAt(data.generated_at);
        // Load thresholds from backend, fallback to defaults
        if (data.thresholds) {
          setThresholds({ ...DEFAULT_THRESHOLDS, ...data.thresholds });
        }
        // Load GLI (Global Liquidity Index) status
        if (data.gli) {
          setGli(data.gli);
        }
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
    // Filter out assets below minimum score threshold (from config)
    // Leaders are ALWAYS shown regardless of score to ensure visibility of deteriorating positions
    const minScore = thresholds.min_display_score;
    const qualified = assets.filter(a =>
      (a.composite || 0) >= minScore || a.tier === 'leader'
    );

    const sorted = [...qualified].sort((a, b) => {
      const aStrong = a.action === 'strong-accumulate' ? 0 : 1;
      const bStrong = b.action === 'strong-accumulate' ? 0 : 1;
      const tierDiff = (TIER_CONFIG[a.tier]?.order || 0) - (TIER_CONFIG[b.tier]?.order || 0);
      if (tierDiff !== 0) return tierDiff;
      if (aStrong !== bStrong) return aStrong - bStrong;
      return (b.composite || 0) - (a.composite || 0);
    });
    if (activeTier === 'all') return sorted;
    return sorted.filter(a => a.tier === activeTier);
  }, [activeTier, assets, thresholds.min_display_score]);

  const groupedAssets = useMemo(() => {
    const groups = { leader: [], 'runner-up': [], observation: [] };
    filteredAssets.forEach(a => {
      if (groups[a.tier]) {
        groups[a.tier].push(a);
      } else {
        console.warn(`Unknown tier "${a.tier}" for asset ${a.symbol}, skipping`);
      }
    });
    return groups;
  }, [filteredAssets]);

  const strongCount = assets.filter(a => a.action === 'strong-accumulate' && (a.composite || 0) >= thresholds.min_display_score).length;

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
      {/* Minimal header: title + metadata */}
      <div style={{ maxWidth: '1400px', margin: `0 auto ${SPACE.lg}px` }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', flexWrap: 'wrap', gap: `${SPACE.sm}px` }}>
          <h1 style={{ fontSize: isMobile ? '1.5rem' : '1.75rem', fontWeight: 400, margin: 0, letterSpacing: '-0.01em', lineHeight: 1, color: PALETTE.textPrimary }}>
            Conviction Board
          </h1>
          <div style={{ fontSize: TYPE.small, color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace', display: 'flex', alignItems: 'center', gap: `${SPACE.sm}px`, flexWrap: 'wrap' }}>
            {generatedAt && (
              <>
                {isStale(generatedAt, thresholds.stale_hours) && <AlertCircle size={12} color="#d49a6a" strokeWidth={2} />}
                <span style={{ color: isStale(generatedAt, thresholds.stale_hours) ? '#d49a6a' : PALETTE.textMuted }}>
                  {relativeTime(generatedAt)}
                </span>
              </>
            )}
            {gli && gli.enabled && gli.source !== 'fallback' && (
              <span style={{ color: gli.downtrend ? '#d49a6a' : '#6a9a90' }}>
                · GLI {gli.downtrend ? '▼' : '▲'}
              </span>
            )}
          </div>
        </div>
      </div>

      <ActionSummary assets={assets} isMobile={isMobile} minScore={thresholds.min_display_score} strongCount={strongCount} gli={gli} />

      <div style={{ maxWidth: '1400px', margin: `0 auto ${SPACE.base}px` }}>
        <select
          value={activeTier}
          onChange={(e) => setActiveTier(e.target.value)}
          style={{
            background: PALETTE.cardBg,
            color: PALETTE.textPrimary,
            border: `1px solid ${PALETTE.border}`,
            padding: `${SPACE.sm}px ${SPACE.md}px`,
            paddingRight: `${SPACE.xl}px`,
            fontSize: TYPE.small,
            fontFamily: 'ui-monospace, monospace',
            letterSpacing: '0.04em',
            cursor: 'pointer',
            appearance: 'none',
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23a39a8a' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
            backgroundRepeat: 'no-repeat',
            backgroundPosition: `right ${SPACE.sm}px center`,
            minWidth: isMobile ? '50%' : '180px',
            maxWidth: isMobile ? '60%' : '220px',
          }}
        >
          <option value="all">All tiers</option>
          <option value="leader">Leaders</option>
          <option value="runner-up">Runner-ups</option>
          <option value="observation">Observation</option>
        </select>
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
                <h2 style={{ fontSize: TYPE.small, letterSpacing: '0.15em', textTransform: 'uppercase', color: config.accent, fontFamily: 'ui-monospace, monospace', fontWeight: 500, margin: 0 }}>
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
                  fontSize: TYPE.body,
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

      {/* Footer with strategy and reference info */}
      <div style={{ maxWidth: '1400px', margin: `${isMobile ? SPACE['2xl'] : SPACE['3xl']}px auto 0`, borderTop: `1px solid ${PALETTE.border}`, paddingTop: `${SPACE.lg}px` }}>
        <StrategySection isMobile={isMobile} />
        <ActionLegend isMobile={isMobile} />
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(240px, 1fr))', gap: `${SPACE.lg}px`, fontSize: TYPE.small, color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace', letterSpacing: '0.03em', lineHeight: TYPE.relaxed, marginTop: `${SPACE.lg}px` }}>
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
