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

// Default category weights — mirrors pipeline/config.yaml weights_by_category; overridden by latest.json
const DEFAULT_WEIGHTS_BY_TYPE = {
  'monetary-store-of-value': { institutional: 0.40, supply: 0.35, regulatory: 0.25 },
  'smart-contract-platform': { institutional: 0.25, adoption_activity: 0.20, value_capture: 0.20, supply: 0.20, regulatory: 0.15 },
  'defi-protocol': { value_capture: 0.30, adoption_activity: 0.15, institutional: 0.20, regulatory: 0.15, supply: 0.20 },
  'oracle-data': { institutional: 0.25, adoption_activity: 0.25, regulatory: 0.20, value_capture: 0.15, supply: 0.15 },
  'enterprise-settlement': { institutional: 0.30, adoption_activity: 0.25, regulatory: 0.25, supply: 0.20 },
  'payments-rail': { institutional: 0.35, adoption_activity: 0.20, regulatory: 0.30, supply: 0.15 },
  'shared-security': { adoption_activity: 0.25, value_capture: 0.25, institutional: 0.20, regulatory: 0.15, supply: 0.15 },
  'data-availability-modular': { adoption_activity: 0.25, value_capture: 0.20, institutional: 0.20, regulatory: 0.15, supply: 0.20 },
  'ai-compute-depin': { adoption_activity: 0.25, value_capture: 0.20, institutional: 0.20, supply: 0.20, regulatory: 0.15 },
  'default': { institutional: 0.25, adoption_activity: 0.20, value_capture: 0.20, supply: 0.20, regulatory: 0.15 },
  // Legacy asset_type keys (pre–asset_category JSON)
  'store-of-value': { institutional: 0.40, supply: 0.35, regulatory: 0.25 },
  'smart-contract': { institutional: 0.25, adoption_activity: 0.20, value_capture: 0.20, supply: 0.20, regulatory: 0.15 },
  'defi': { value_capture: 0.30, adoption_activity: 0.15, institutional: 0.20, regulatory: 0.15, supply: 0.20 },
  'infrastructure': { institutional: 0.25, adoption_activity: 0.20, value_capture: 0.20, supply: 0.20, regulatory: 0.15 },
};

let WEIGHTS_BY_TYPE = DEFAULT_WEIGHTS_BY_TYPE;

function setWeightProfiles(profiles) {
  if (profiles && typeof profiles === 'object') {
    WEIGHTS_BY_TYPE = { ...DEFAULT_WEIGHTS_BY_TYPE, ...profiles };
  }
}

const LEGACY_ASSET_TYPE_TO_CATEGORY = {
  'store-of-value': 'monetary-store-of-value',
  'smart-contract': 'smart-contract-platform',
  'defi': 'defi-protocol',
};

function resolveWeightKey(assetOrKey) {
  if (typeof assetOrKey === 'string') {
    if (WEIGHTS_BY_TYPE[assetOrKey]) return assetOrKey;
    return LEGACY_ASSET_TYPE_TO_CATEGORY[assetOrKey] || 'default';
  }
  const a = assetOrKey || {};
  if (a.asset_category && WEIGHTS_BY_TYPE[a.asset_category]) return a.asset_category;
  const mapped = a.asset_type && LEGACY_ASSET_TYPE_TO_CATEGORY[a.asset_type];
  if (mapped && WEIGHTS_BY_TYPE[mapped]) return mapped;
  if (a.asset_type && WEIGHTS_BY_TYPE[a.asset_type]) return a.asset_type;
  return 'default';
}

function getWeights(assetOrKey) {
  const key = resolveWeightKey(assetOrKey);
  return WEIGHTS_BY_TYPE[key] || WEIGHTS_BY_TYPE['default'];
}

const PALETTE = {
  bg: '#121110',
  cardBg: '#1a1816',
  cardInset: '#211e1b',
  border: '#3a342d',
  borderStrong: '#55493c',
  textPrimary: '#ede7d9',
  // Was #a39a8a (~6.4:1) → now ~9.6:1 for comfortable long-form reading
  // on dark backgrounds. Keeps warm tint to match palette. Avoids pure
  // white to prevent halation on Georgia italic body text.
  textSecondary: '#d3c8b4',
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

// Type scale: rem-based for accessibility
// Desktop root is 18px, mobile is 16px (set in index.html)
const TYPE = {
  // Sizes (desktop effective: multiply by 1.125)
  caption: '0.8125rem',  // 13px mobile, 14.6px desktop - labels
  small: '0.875rem',     // 14px mobile, 15.75px desktop - secondary text
  body: '1rem',          // 16px mobile, 18px desktop - body copy
  base: '1.125rem',      // 18px mobile, 20.25px desktop - emphasized body
  subhead: '1.25rem',    // 20px mobile, 22.5px desktop - subheadings
  heading: '1.5rem',     // 24px mobile, 27px desktop - card headings
  title: '2rem',         // 32px mobile, 36px desktop - page title
  display: '2.5rem',     // 40px mobile, 45px desktop - large numbers
  displayLg: '3rem',     // 48px mobile, 54px desktop - large numbers
  // Line heights
  tight: 1.1,
  snug: 1.25,
  normal: 1.5,
  relaxed: 1.65,
};

const DIMENSION_LABELS = {
  institutional: 'Institutional',
  adoption_activity: 'Adoption / Activity',
  value_capture: 'Value capture',
  revenue: 'Revenue/Fees (legacy)',
  regulatory: 'Regulatory',
  supply: 'Supply / On-chain',
  wyckoff: 'Wyckoff (filter)',
};

/** Short labels for decision_trace.downgrades.reasons (backend codes). */
const DECISION_REASON_LABELS = {
  'macro:gli_contracting': 'GLI contracting',
  'macro:rs_underperforming_btc': 'RS vs BTC weak',
  'macro:fear_greed_euphoria': 'Fear & Greed euphoria',
  'wyckoff:markup': 'Wyckoff markup',
  'wyckoff:distribution_or_markdown': 'Wyckoff distribution / markdown',
  'leader_capitulation_both_rsi': 'Leader capitulation (weekly + daily RSI < 30)',
  'leader_capitulation_weekly_only': 'Leader capitulation (weekly RSI < 30)',
  'leader_wyckoff_weekly_slope_downgrade': 'Leader Wyckoff setup reduced by weak weekly slope',
  'leader_wyckoff_strong_accumulate': 'Leader strong-accumulate Wyckoff setup',
  'leader_wyckoff_accumulate': 'Leader accumulate Wyckoff setup',
  'leader_hold_default': 'Leader hold default (no active accumulate trigger)',
  'stand_aside_sharp_decline': 'Stand aside due to sharp decline',
  'runner_up_promote': 'Runner-up promoted',
  'runner_up_await': 'Runner-up awaiting confirmation',
  'observe_default': 'Observation default',
};

const ASSET_TYPE_LABELS = {
  'store-of-value': 'Store of Value',
  'smart-contract': 'Smart Contract',
  'defi': 'DeFi',
  'infrastructure': 'Infrastructure',
};

const ASSET_CATEGORY_LABELS = {
  'monetary-store-of-value': 'Monetary (SoV)',
  'smart-contract-platform': 'Smart contract L1',
  'defi-protocol': 'DeFi',
  'oracle-data': 'Oracle / data',
  'enterprise-settlement': 'Enterprise settlement',
  'payments-rail': 'Payments rail',
  'shared-security': 'Shared security',
  'data-availability-modular': 'Modular DA',
  'ai-compute-depin': 'AI / DePIN',
  'default': 'Default',
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

function computeComposite(scores, assetOrKey) {
  const weights = getWeights(assetOrKey);
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

  // Helpers to safely format RSI values that may be null/undefined.
  const hasRsi = (v) => typeof v === 'number' && !isNaN(v);
  const fmtRsi = (v) => (hasRsi(v) ? v : 'n/a');

  // Detect if this is a capitulation signal (RSI-driven) vs Wyckoff-driven
  const isCapitulation = hasRsi(rsiWeekly) && rsiWeekly < 30;
  const isDeepCapitulation = isCapitulation && hasRsi(rsiDaily) && rsiDaily < 30;

  switch (action) {
    case 'strong-accumulate':
      if (isDeepCapitulation) {
        return `Capitulation detected: both daily RSI (${fmtRsi(rsiDaily)}) and weekly RSI (${fmtRsi(rsiWeekly)}) below 30. This panic selling in a quality leader is historically a strong entry point. Fundamentals intact at ${composite}.`;
      }
      return `Daily RSI at ${fmtRsi(rsiDaily)} signals short-term oversold while weekly RSI (${fmtRsi(rsiWeekly)}) and composite (${composite}) remain healthy. This dislocation within an accumulation zone is a high-conviction entry point.`;
    case 'accumulate':
      if (isCapitulation) {
        return `Weekly RSI at ${fmtRsi(rsiWeekly)} signals capitulation-level oversold. Quality leaders typically recover from panic selling. Consider measured accumulation while fundamentals remain intact (composite ${composite}).`;
      }
      return `Composite score of ${composite} with ${delta >= 0 ? 'stable' : 'minor pullback'} trend. RSI levels support accumulation. Leader-tier asset in favorable Wyckoff phase for tranche building.`;
    case 'promote':
      return `Runner-up crossing leader threshold with composite at ${composite}${delta30 > 0 ? ` and +${delta30}-point 30-day momentum` : ''}. Evaluate for potential tier promotion.`;
    case 'hold':
      return `Position active with composite at ${composite}. No accumulate or trim signals present. Current allocation appropriate — patience is the strategy.`;
    case 'await':
      return `Signal building but not yet confirmed. Composite at ${composite}${delta > 0 ? ` with ${delta}-point uptick` : ''}. Monitor for entry criteria before activation.`;
    case 'observe':
      return `Observation tier — scanning only. ${composite >= 75 ? 'Composite healthy but' : 'Composite at ' + composite + ','} no position warranted at this time.`;
    case 'stand-aside': {
      const weeklyElevated = hasRsi(rsiWeekly) && rsiWeekly >= 70;
      const wyckoff = (asset.wyckoff_phase || '').toLowerCase();
      const isDistribution = wyckoff.includes('distribution');
      const reason = isDistribution
        ? 'Distribution phase detected'
        : delta < -3
          ? `Sharp composite decline (${Math.abs(delta)} pts this week)`
          : 'Structural weakness detected';
      return `${reason}${weeklyElevated ? ` with elevated weekly RSI (${rsiWeekly})` : ''}. Capital preservation takes priority — do not engage.`;
    }
    default:
      return null;
  }
}

function DecisionTraceSection({ trace, isMobile }) {
  const [expanded, setExpanded] = useState(false);
  if (!trace || typeof trace !== 'object' || !trace.path) {
    return null;
  }

  const dg = trace.downgrades || {};
  const levels = typeof dg.levels_applied === 'number' ? dg.levels_applied : 0;
  const reasons = Array.isArray(dg.reasons) ? dg.reasons : [];
  const pathLabel = DECISION_REASON_LABELS[trace.path] || String(trace.path).replace(/_/g, ' ');

  return (
    <div style={{ marginBottom: isMobile ? SPACE.xl : SPACE.lg }}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        style={{
          background: 'transparent',
          border: `1px solid ${PALETTE.border}`,
          color: PALETTE.textMuted,
          padding: isMobile ? `${SPACE.md}px ${SPACE.base}px` : `${SPACE.sm}px ${SPACE.md}px`,
          fontSize: TYPE.caption,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          fontFamily: 'ui-monospace, monospace',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: `${SPACE.sm}px`,
          minHeight: isMobile ? '44px' : 'auto',
          width: '100%',
        }}
      >
        <span style={{
          transition: 'transform 0.2s',
          display: 'inline-block',
          transform: expanded ? 'rotate(90deg)' : 'none',
        }}>▸</span>
        <span>Why this action</span>
      </button>

      {expanded && (
        <div style={{
          marginTop: `${SPACE.sm}px`,
          padding: isMobile ? SPACE.base : SPACE.md,
          background: PALETTE.cardInset,
          border: `1px solid ${PALETTE.border}`,
        }}>
          <p style={{
            margin: 0,
            fontSize: TYPE.caption,
            fontFamily: 'ui-monospace, monospace',
            color: PALETTE.textMuted,
            letterSpacing: '0.04em',
            lineHeight: TYPE.relaxed,
            maxWidth: '50ch',
          }}>
            Path: {pathLabel}
          </p>
          {trace.base_action && trace.final_action && trace.base_action !== trace.final_action && (
            <p style={{
              margin: `${SPACE.sm}px 0 0`,
              fontFamily: 'ui-monospace, monospace',
              fontSize: TYPE.small,
              color: PALETTE.textSecondary,
            }}>
              {trace.base_action} → {trace.final_action}
            </p>
          )}
          {levels > 0 && (
            <p style={{
              margin: `${SPACE.sm}px 0 0`,
              fontSize: TYPE.caption,
              color: PALETTE.textMuted,
              fontFamily: 'ui-monospace, monospace',
            }}>
              Downgrade levels: {levels} (macro {dg.macro_levels ?? 0}, Wyckoff {dg.wyckoff_levels ?? 0})
            </p>
          )}
          {reasons.length > 0 && (
            <ul style={{
              margin: `${SPACE.sm}px 0 0`,
              paddingLeft: `${SPACE.lg}px`,
              fontFamily: 'Georgia, serif',
              fontSize: TYPE.small,
              color: PALETTE.textSecondary,
              lineHeight: TYPE.relaxed,
            }}>
              {reasons.map((r, i) => (
                <li key={i} style={{ marginBottom: `${SPACE.xs}px` }}>
                  {DECISION_REASON_LABELS[r] || r}
                </li>
              ))}
            </ul>
          )}
          {trace.summary && (
            <p style={{
              margin: `${SPACE.base}px 0 0`,
              fontSize: TYPE.small,
              color: PALETTE.textSecondary,
              fontFamily: 'Georgia, serif',
              fontStyle: 'italic',
              lineHeight: TYPE.relaxed,
              maxWidth: '55ch',
            }}>
              {trace.summary}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// Human-readable labels for downgrade reasons (matches backend _DOWNGRADE_REASON_COPY)
const DOWNGRADE_REASON_LABELS = {
  'macro:gli_contracting': 'global liquidity is contracting',
  'macro:rs_underperforming_btc': 'relative strength vs BTC is weak',
  'macro:fear_greed_euphoria': 'market sentiment is euphoric',
  'wyckoff:markup': 'Wyckoff structure is already in markup',
  'wyckoff:distribution_or_markdown': 'Wyckoff structure is distribution/markdown',
};

// Build concise decision logic explanation
function buildDecisionLogic(trace, tier, macroDowngrades, wyckoffDowngrades) {
  if (!trace) return null;

  const downgrades = trace.downgrades || {};
  const downgradeReasons = Array.isArray(downgrades.reasons) ? downgrades.reasons : [];
  const inputMacroReasons = Array.isArray(trace.inputs?.macro_reasons) ? trace.inputs.macro_reasons : [];
  const inputWyckoffReasons = Array.isArray(trace.inputs?.wyckoff_reasons) ? trace.inputs.wyckoff_reasons : [];
  // Combine + de-duplicate while preserving order to avoid repeated copy in UI.
  const reasons = [...new Set([...downgradeReasons, ...inputMacroReasons, ...inputWyckoffReasons])];

  const inferredBaseAction =
    (!trace.base_action && trace.final_action === 'hold' && tier === 'leader' && trace.inputs?.macro_downgrade_active)
      ? 'accumulate'
      : null;
  const baseAction = trace.base_action || inferredBaseAction;

  const hasActionDowngrade = Boolean(
    baseAction &&
    trace.final_action &&
    baseAction !== trace.final_action
  );
  const hasReasonDowngrade = reasons.length > 0 || trace.inputs?.macro_downgrade_active;
  const hasDowngrades =
    (macroDowngrades > 0) ||
    (wyckoffDowngrades > 0) ||
    hasActionDowngrade ||
    hasReasonDowngrade;

  let parts = [];

  // Tier
  parts.push(`${tier.charAt(0).toUpperCase() + tier.slice(1)} tier`);

  // Downgrade status
  if (!hasDowngrades) {
    parts.push('no downgrades active');
  } else {
    const downgradeDesc = [];
    const macroReasons = reasons.filter(r => r.startsWith('macro:'));
    if (macroDowngrades > 0 || macroReasons.length > 0) {
      const readableReasons = macroReasons.map(r => DOWNGRADE_REASON_LABELS[r] || r.replace('macro:', ''));
      if (readableReasons.length > 0) {
        downgradeDesc.push(`macro (${readableReasons.join(', ')})`);
      } else if (macroDowngrades > 0) {
        downgradeDesc.push('macro');
      }
    }
    const wyckReasons = reasons.filter(r => r.startsWith('wyckoff:'));
    if (wyckoffDowngrades > 0 || wyckReasons.length > 0) {
      const readableReasons = wyckReasons.map(r => DOWNGRADE_REASON_LABELS[r] || r.replace('wyckoff:', ''));
      if (readableReasons.length > 0) {
        downgradeDesc.push(`Wyckoff (${readableReasons.join(', ')})`);
      } else if (wyckoffDowngrades > 0) {
        downgradeDesc.push('Wyckoff');
      }
    }
    if (hasActionDowngrade) {
      parts.push(`downgraded from ${baseAction} to ${trace.final_action}`);
      if (downgradeDesc.length > 0) {
        parts.push(`due to ${downgradeDesc.join(' and ')}`);
      }
    } else if (trace.inputs?.macro_downgrade_active && downgradeDesc.length > 0) {
      parts.push(`macro filters active (${downgradeDesc.join(' and ')})`);
    } else if (downgradeDesc.length > 0) {
      parts.push(`${downgradeDesc.join(' and ')} filters active`);
    }
  }

  return parts.join(', ') + '.';
}

function DetailModal({ asset, onClose, isMobile, gli, rs, fearGreed }) {
  // Collapsible section state
  const [dimensionsExpanded, setDimensionsExpanded] = useState(false);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [technicalExpanded, setTechnicalExpanded] = useState(false);

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

  const tier = asset.tier || 'observation';
  const config = TIER_CONFIG[tier];
  const TierIcon = config?.icon || Eye;
  const assetType = asset.asset_type || 'smart-contract';
  const catLabel = asset.asset_category
    ? (ASSET_CATEGORY_LABELS[asset.asset_category] || asset.asset_category)
    : null;
  const weights = asset.weights || getWeights(asset);
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
  const weightedDimensions = sortedDimensions.filter(dim => dim !== 'wyckoff');
  // Clean up Wyckoff rationale - remove implementation details
  const rawWyckoffRationale = asset.score_rationales?.wyckoff;
  const wyckoffRationale = rawWyckoffRationale
    ? rawWyckoffRationale.replace(/^Manual override:\s*/i, '')
    : null;
  const decisionDowngrades = asset.decision_trace?.downgrades || {};
  const macroDowngrades = decisionDowngrades.macro_levels ?? 0;
  const wyckoffDowngrades = decisionDowngrades.wyckoff_levels ?? 0;
  const hasDowngrades = macroDowngrades > 0 || wyckoffDowngrades > 0;
  const showRsContext = rs && rs.enabled && asset.symbol !== 'BTC' && asset.rs_vs_btc;
  const gliTrendLabel = gli?.trend || (gli?.downtrend ? 'contracting' : 'expanding');
  const gliNeutral = gli?.enabled && !gli?.downtrend;
  const fgClassification = fearGreed?.classification || 'N/A';
  const fgValue = typeof fearGreed?.value === 'number' ? fearGreed.value : null;
  const fgNeutral = fearGreed?.enabled && fgValue !== null && fgValue < 70;
  const rsNeutral = showRsContext && !asset.rs_vs_btc.underperforming;

  // Build concise decision logic
  const decisionLogic = buildDecisionLogic(asset.decision_trace, tier, macroDowngrades, wyckoffDowngrades);

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
          maxWidth: '600px',
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
              {asset.name}
              {catLabel ? ` · ${catLabel}` : ''}
              {' · '}{ASSET_TYPE_LABELS[assetType] || assetType}
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
        <div style={{ padding: isMobile ? `${SPACE.lg}px ${SPACE.base}px` : SPACE.lg }}>
          {/* Action banner */}
          <div style={{
            background: cfg?.bg || 'transparent',
            border: cfg?.border ? `1px solid ${cfg.dot}` : 'none',
            padding: `${SPACE.md}px ${SPACE.base}px`,
            marginBottom: isMobile ? SPACE.base : SPACE.lg,
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
              <div style={{ fontSize: TYPE.caption, color: cfg?.fg || PALETTE.textSecondary, fontFamily: 'ui-monospace, monospace', marginTop: 2 }}>
                {cfg?.desc}
              </div>
            </div>
          </div>

          {/* Why this action - concise decision logic */}
          {decisionLogic && (
            <div style={{
              fontSize: TYPE.small,
              color: PALETTE.textSecondary,
              fontFamily: 'ui-monospace, monospace',
              lineHeight: TYPE.relaxed,
              marginBottom: isMobile ? SPACE.xl : SPACE.lg,
              padding: `${SPACE.md}px ${SPACE.base}px`,
              background: PALETTE.cardInset,
              border: `1px solid ${PALETTE.border}`,
            }}>
              {decisionLogic}
            </div>
          )}

          {/* Score section - increased spacing for emphasis */}
          <div style={{
            marginTop: isMobile ? SPACE['2xl'] : SPACE.xl,
            marginBottom: isMobile ? SPACE.lg : SPACE.base,
          }}>
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
            <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm, fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: isMobile ? SPACE.base : SPACE.lg, fontFamily: 'ui-monospace, monospace' }}>
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
          </div>

          {/* Weighted dimensions - visual summary */}
          <div style={{
            marginTop: isMobile ? SPACE['2xl'] : SPACE.xl,
            marginBottom: isMobile ? SPACE.lg : SPACE.base,
          }}>
            <div style={{ fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: SPACE.base, fontFamily: 'ui-monospace, monospace' }}>
              Weighted dimensions
            </div>
            {weightedDimensions.map(dim => (
              <DimensionBar
                key={dim}
                label={DIMENSION_LABELS[dim] || dim}
                value={asset.scores?.[dim]}
                accent={config?.accent}
                weight={weights[dim]}
              />
            ))}
          </div>

          {/* Dimension Evidence - verbose explanations */}
          <div style={{ marginTop: SPACE.base, marginBottom: isMobile ? SPACE['2xl'] : SPACE.xl }}>
            <button
              onClick={() => setDimensionsExpanded(!dimensionsExpanded)}
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                width: '100%',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: dimensionsExpanded ? SPACE.base : 0,
              }}
            >
              <div style={{ fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace' }}>
                Dimension evidence {!dimensionsExpanded && '· Tap to expand'}
              </div>
              <span style={{
                display: 'inline-block',
                transform: dimensionsExpanded ? 'rotate(90deg)' : 'none',
                transition: 'transform 0.2s ease',
                color: PALETTE.textMuted,
              }}>▸</span>
            </button>

            {dimensionsExpanded && (
              <div style={{ marginTop: SPACE.base, display: 'grid', gap: SPACE.lg }}>
                {weightedDimensions.map(dim => {
                  const rationale = asset.score_rationales?.[dim];
                  const score = asset.scores?.[dim];
                  const weight = weights[dim];
                  // Skip dimensions with missing rationale or null/undefined scores
                  if (!rationale || score === null || score === undefined) return null;

                  return (
                    <div key={dim}>
                      <div style={{
                        fontSize: TYPE.small,
                        fontFamily: 'ui-monospace, monospace',
                        color: PALETTE.textMuted,
                        marginBottom: SPACE.xs,
                      }}>
                        {DIMENSION_LABELS[dim] || dim} ({score}/100, {Math.round(weight * 100)}% weight)
                      </div>
                      <div style={{
                        fontSize: TYPE.small,
                        color: PALETTE.textSecondary,
                        fontFamily: 'Georgia, serif',
                        lineHeight: TYPE.relaxed,
                        maxWidth: '60ch',
                      }}>
                        {rationale}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Global filters - list all filters with color coding */}
          <div style={{ marginTop: isMobile ? SPACE['2xl'] : SPACE.xl, paddingTop: isMobile ? SPACE.lg : SPACE.md, borderTop: `1px solid ${PALETTE.border}` }}>
            <div style={{ fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, marginBottom: SPACE.base, fontFamily: 'ui-monospace, monospace' }}>
              Global filters
            </div>
            <div style={{ fontSize: TYPE.caption, color: PALETTE.textMuted, fontFamily: 'Georgia, serif', lineHeight: TYPE.relaxed, marginBottom: SPACE.base, maxWidth: '50ch' }}>
              Filters that can downgrade signals regardless of dimension scores.
            </div>
            <div style={{ display: 'grid', rowGap: SPACE.sm }}>
              {/* Wyckoff Phase */}
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: SPACE.base, fontSize: TYPE.small }}>
                <span style={{ fontFamily: 'ui-monospace, monospace', color: PALETTE.textMuted }}>Wyckoff</span>
                <span style={{
                  textAlign: 'right',
                  color: (asset.wyckoff_phase && (asset.wyckoff_phase.toLowerCase().includes('distribution') || asset.wyckoff_phase.toLowerCase().includes('markdown'))) ? '#c27878' : '#7aa872'
                }}>
                  {asset.wyckoff_phase || 'Unknown'}
                </span>
              </div>
              {/* RS vs BTC - show for all assets */}
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: SPACE.base, fontSize: TYPE.small }}>
                <span style={{ fontFamily: 'ui-monospace, monospace', color: PALETTE.textMuted }}>RS vs BTC</span>
                {asset.symbol === 'BTC' ? (
                  <span style={{ textAlign: 'right', color: PALETTE.textMuted }}>N/A (self)</span>
                ) : showRsContext ? (
                  <span style={{ textAlign: 'right', color: rsNeutral ? '#7aa872' : '#c27878' }}>
                    {asset.rs_vs_btc.underperforming ? 'Underperforming' : 'Holding'}
                    {typeof asset.rs_vs_btc.change_pct === 'number' ? ` ${asset.rs_vs_btc.change_pct > 0 ? '+' : ''}${(asset.rs_vs_btc.change_pct * 100).toFixed(1)}%` : ''}
                  </span>
                ) : (
                  <span style={{ textAlign: 'right', color: PALETTE.textMuted }}>N/A</span>
                )}
              </div>
              {/* GLI - show always */}
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: SPACE.base, fontSize: TYPE.small }}>
                <span style={{ fontFamily: 'ui-monospace, monospace', color: PALETTE.textMuted }}>GLI</span>
                {gli?.enabled ? (
                  <span style={{ textAlign: 'right', color: gliNeutral ? '#7aa872' : '#c27878' }}>{gliTrendLabel}</span>
                ) : (
                  <span style={{ textAlign: 'right', color: PALETTE.textMuted }}>Disabled</span>
                )}
              </div>
              {/* Fear & Greed - show always */}
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: SPACE.base, fontSize: TYPE.small }}>
                <span style={{ fontFamily: 'ui-monospace, monospace', color: PALETTE.textMuted }}>Fear & Greed</span>
                {fearGreed?.enabled ? (
                  <span style={{ textAlign: 'right', color: fgNeutral ? '#7aa872' : '#c27878' }}>{fgClassification}{fgValue !== null ? ` (${fgValue})` : ''}</span>
                ) : (
                  <span style={{ textAlign: 'right', color: PALETTE.textMuted }}>Disabled</span>
                )}
              </div>
            </div>
          </div>

          {/* Technical Analysis - detailed reasoning for filters */}
          <div style={{ marginTop: isMobile ? SPACE['2xl'] : SPACE.lg, paddingTop: isMobile ? SPACE.lg : SPACE.md, borderTop: `1px solid ${PALETTE.border}` }}>
            <button
              onClick={() => setTechnicalExpanded(!technicalExpanded)}
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                width: '100%',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: technicalExpanded ? SPACE.base : 0,
              }}
            >
              <div style={{ fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textMuted, fontFamily: 'ui-monospace, monospace' }}>
                Technical analysis {!technicalExpanded && '· Tap to expand'}
              </div>
              <span style={{
                display: 'inline-block',
                transform: technicalExpanded ? 'rotate(90deg)' : 'none',
                transition: 'transform 0.2s ease',
                color: PALETTE.textMuted,
              }}>▸</span>
            </button>
            {technicalExpanded && (
              <div style={{ marginTop: SPACE.base, display: 'grid', gap: SPACE.lg }}>
                {/* Wyckoff Phase Analysis */}
                {wyckoffRationale && (
                  <div>
                    <div style={{
                      fontSize: TYPE.small,
                      fontFamily: 'ui-monospace, monospace',
                      color: PALETTE.textMuted,
                      marginBottom: SPACE.xs,
                    }}>
                      Wyckoff Phase: {asset.wyckoff_phase || 'Unknown'}
                    </div>
                    <div style={{
                      fontSize: TYPE.small,
                      color: PALETTE.textSecondary,
                      fontFamily: 'Georgia, serif',
                      lineHeight: TYPE.relaxed,
                      maxWidth: '60ch',
                    }}>
                      {wyckoffRationale}
                    </div>
                  </div>
                )}

                {/* RSI Analysis */}
                {(
                  (typeof asset.rsi_daily === 'number' && !isNaN(asset.rsi_daily)) ||
                  (typeof asset.rsi_weekly === 'number' && !isNaN(asset.rsi_weekly))
                ) && (
                  <div>
                    <div style={{
                      fontSize: TYPE.small,
                      fontFamily: 'ui-monospace, monospace',
                      color: PALETTE.textMuted,
                      marginBottom: SPACE.xs,
                    }}>
                      RSI
                    </div>
                    <div style={{
                      fontSize: TYPE.small,
                      color: PALETTE.textSecondary,
                      fontFamily: 'Georgia, serif',
                      lineHeight: TYPE.relaxed,
                    }}>
                      {(typeof asset.rsi_daily === 'number' && !isNaN(asset.rsi_daily)) && `Daily: ${asset.rsi_daily.toFixed(1)}`}
                      {(typeof asset.rsi_daily === 'number' && !isNaN(asset.rsi_daily)) && (typeof asset.rsi_weekly === 'number' && !isNaN(asset.rsi_weekly)) && ' · '}
                      {(typeof asset.rsi_weekly === 'number' && !isNaN(asset.rsi_weekly)) && `Weekly: ${asset.rsi_weekly.toFixed(1)}`}
                    </div>
                  </div>
                )}

                {/* GLI Analysis - show always */}
                <div>
                  <div style={{
                    fontSize: TYPE.small,
                    fontFamily: 'ui-monospace, monospace',
                    color: PALETTE.textMuted,
                    marginBottom: SPACE.xs,
                  }}>
                    Global Liquidity Index
                  </div>
                  <div style={{
                    fontSize: TYPE.small,
                    color: PALETTE.textSecondary,
                    fontFamily: 'Georgia, serif',
                    lineHeight: TYPE.relaxed,
                    maxWidth: '60ch',
                  }}>
                    {gli?.enabled ? (
                      <>
                        {gliTrendLabel.charAt(0).toUpperCase() + gliTrendLabel.slice(1)}
                        {gli.current && gli.offset_value && ` (current: $${gli.current.toFixed(1)}T vs ${gli.offset_days}d ago: $${gli.offset_value.toFixed(1)}T)`}
                        {'. '}
                        {gli.downtrend ? 'Filter active: liquidity contracting, downgrades accumulate signals.' : 'Filter neutral: liquidity expanding, no downgrade.'}
                        {gli.source && ` Source: ${gli.source}.`}
                      </>
                    ) : (
                      'Filter disabled in configuration.'
                    )}
                  </div>
                </div>

                {/* RS vs BTC Analysis - show for all assets */}
                <div>
                  <div style={{
                    fontSize: TYPE.small,
                    fontFamily: 'ui-monospace, monospace',
                    color: PALETTE.textMuted,
                    marginBottom: SPACE.xs,
                  }}>
                    Relative Strength vs BTC
                  </div>
                  <div style={{
                    fontSize: TYPE.small,
                    color: PALETTE.textSecondary,
                    fontFamily: 'Georgia, serif',
                    lineHeight: TYPE.relaxed,
                  }}>
                    {asset.symbol === 'BTC' ? (
                      'Not applicable — cannot compare BTC to itself.'
                    ) : showRsContext ? (
                      <>
                        {asset.rs_vs_btc.underperforming ? 'Underperforming' : 'Holding or outperforming'} BTC
                        {typeof asset.rs_vs_btc.change_pct === 'number' && ` by ${asset.rs_vs_btc.change_pct > 0 ? '+' : ''}${(asset.rs_vs_btc.change_pct * 100).toFixed(1)}%`}
                        {` over ${rs?.lookback_days || 90} days`}
                        {asset.rs_vs_btc.underperforming && '. Filter active: downgrades accumulate signals.'}
                        {!asset.rs_vs_btc.underperforming && '. Filter neutral: no downgrade.'}
                      </>
                    ) : (
                      'Data not available.'
                    )}
                  </div>
                </div>

                {/* Fear & Greed Analysis - show always */}
                <div>
                  <div style={{
                    fontSize: TYPE.small,
                    fontFamily: 'ui-monospace, monospace',
                    color: PALETTE.textMuted,
                    marginBottom: SPACE.xs,
                  }}>
                    Fear & Greed Index
                  </div>
                  <div style={{
                    fontSize: TYPE.small,
                    color: PALETTE.textSecondary,
                    fontFamily: 'Georgia, serif',
                    lineHeight: TYPE.relaxed,
                  }}>
                    {fearGreed?.enabled ? (
                      <>
                        {fgClassification}{fgValue !== null && ` (${fgValue}/100)`}
                        {fgValue !== null && fgValue >= 70 && '. Filter active: extreme greed detected, downgrades accumulate signals.'}
                        {fgValue !== null && fgValue < 70 && '. Filter neutral: sentiment not extreme, no downgrade.'}
                      </>
                    ) : (
                      'Filter disabled in configuration.'
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
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

function ScoreCard({ asset, isMobile, gli, rs, fearGreed }) {
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
    const computed = computeComposite(asset.scores, asset);
    composite = computed.composite;
  }

  const delta = weeklyDelta(asset.trend);
  const config = TIER_CONFIG[asset.tier];
  if (!config) return null;
  const action = asset.action || 'observe';
  const isStrong = action === 'strong-accumulate';
  const cfg = ACTION_CONFIG[action];
  const isUnderperforming = asset.rs_vs_btc && asset.rs_vs_btc.underperforming && asset.symbol !== 'BTC';

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
          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
            <span style={{ fontFamily: 'Georgia, serif', fontSize: isMobile ? TYPE.subhead : TYPE.heading, fontWeight: 400, color: PALETTE.textPrimary, lineHeight: 1 }}>
              {asset.symbol}
            </span>
            {isUnderperforming && (
              <span
                title={`Underperforming BTC by ${Math.abs(asset.rs_vs_btc.change_pct * 100).toFixed(0)}%`}
                style={{
                  fontSize: TYPE.caption,
                  color: '#c89678',
                  fontFamily: 'ui-monospace, monospace',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '2px',
                }}
              >
                <TrendingDown size={10} strokeWidth={2} />
                <span style={{ fontSize: '0.7rem' }}>BTC</span>
              </span>
            )}
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
          gli={gli}
          rs={rs}
          fearGreed={fearGreed}
        />
      )}
    </div>
  );
}

function ActionSummary({ assets, isMobile, minScore = 50, strongCount = 0, gli = null, rs = null }) {
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
      maxWidth: '900px',
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

function GliSection({ gli, isMobile }) {
  const [expanded, setExpanded] = useState(false);

  if (!gli || !gli.enabled || gli.source === 'fallback') {
    return null;
  }

  const offsetDays = gli.offset_days || 75;
  const trend = gli.trend || (gli.downtrend ? 'contracting' : 'expanding');
  const statusColor = trend === 'contracting' ? '#d49a6a' : '#6a9a90';
  const statusText = trend === 'contracting'
    ? '▼ Contracting'
    : trend === 'flat'
      ? '• Flat'
      : '▲ Expanding';

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        style={{
          background: 'transparent',
          border: `1px solid ${PALETTE.border}`,
          color: statusColor,
          padding: `${SPACE.sm}px ${SPACE.md}px`,
          fontSize: TYPE.caption,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          fontFamily: 'ui-monospace, monospace',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: `${SPACE.sm}px`,
          minHeight: isMobile ? '44px' : 'auto',
          width: '100%',
        }}
      >
        <span style={{
          transition: 'transform 0.2s',
          display: 'inline-block',
          transform: expanded ? 'rotate(90deg)' : 'none',
        }}>▸</span>
        <span>GLI {statusText}</span>
        <span style={{ color: PALETTE.textMuted }}>({offsetDays}d offset)</span>
      </button>

      {expanded && (
        <div style={{
          marginTop: `${SPACE.sm}px`,
          padding: `${SPACE.md}px`,
          background: PALETTE.cardBg,
          border: `1px solid ${PALETTE.border}`,
          fontSize: TYPE.small,
          color: PALETTE.textSecondary,
          lineHeight: TYPE.relaxed,
        }}>
          <p style={{ margin: 0 }}>
            <strong style={{ color: PALETTE.textPrimary }}>Global Liquidity Index</strong> tracks aggregate central bank liquidity with a {offsetDays}-day offset.
            When liquidity is contracting (current GLI &lt; {offsetDays} days ago), accumulation signals are downgraded because even quality assets tend to fall further during liquidity withdrawal.
          </p>
          <p style={{ margin: `${SPACE.sm}px 0 0`, fontSize: TYPE.caption, color: PALETTE.textMuted }}>
            Current: {gli.current?.toLocaleString() ?? 'N/A'} | {offsetDays}d ago: {gli.offset_value?.toLocaleString() ?? 'N/A'} | Source: {gli.source}
          </p>
          {(gli.current_obs_date || gli.offset_obs_date) && (
            <p style={{ margin: `${SPACE.xs}px 0 0`, fontSize: TYPE.caption, color: PALETTE.textMuted }}>
              Obs dates: now {gli.current_obs_date || 'N/A'} | offset {gli.offset_obs_date || 'N/A'}
            </p>
          )}
          {(gli.component_coverage !== undefined || (gli.components_used && gli.components_used.length > 0)) && (
            <p style={{ margin: `${SPACE.xs}px 0 0`, fontSize: TYPE.caption, color: PALETTE.textMuted }}>
              Coverage: {Math.round((gli.component_coverage || 0) * 100)}% | Used: {(gli.components_used || []).join(', ') || 'N/A'}
            </p>
          )}
          {gli.components_missing && gli.components_missing.length > 0 && (
            <p style={{ margin: `${SPACE.xs}px 0 0`, fontSize: TYPE.caption, color: '#d49a6a' }}>
              Missing: {gli.components_missing.join(', ')}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function FearGreedSection({ fearGreed, isMobile }) {
  const [expanded, setExpanded] = useState(false);

  if (!fearGreed || !fearGreed.enabled || fearGreed.value === null) {
    return null;
  }

  const isGreedy = fearGreed.greedy;
  const statusColor = isGreedy ? '#d49a6a' : '#6a9a90';
  const value = fearGreed.value;
  const classification = fearGreed.classification || 'Unknown';

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        style={{
          background: 'transparent',
          border: `1px solid ${PALETTE.border}`,
          color: statusColor,
          padding: `${SPACE.sm}px ${SPACE.md}px`,
          fontSize: TYPE.caption,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          fontFamily: 'ui-monospace, monospace',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: `${SPACE.sm}px`,
          minHeight: isMobile ? '44px' : 'auto',
          width: '100%',
        }}
      >
        <span style={{
          transition: 'transform 0.2s',
          display: 'inline-block',
          transform: expanded ? 'rotate(90deg)' : 'none',
        }}>▸</span>
        <span>Fear & Greed: {value}</span>
        <span style={{ color: PALETTE.textMuted }}>({classification})</span>
      </button>

      {expanded && (
        <div style={{
          marginTop: `${SPACE.sm}px`,
          padding: `${SPACE.md}px`,
          background: PALETTE.cardBg,
          border: `1px solid ${PALETTE.border}`,
          fontSize: TYPE.small,
          color: PALETTE.textSecondary,
          lineHeight: TYPE.relaxed,
        }}>
          <p style={{ margin: 0 }}>
            <strong style={{ color: PALETTE.textPrimary }}>Fear & Greed Index</strong> measures market sentiment from 0 (Extreme Fear) to 100 (Extreme Greed).
            When the index reaches {fearGreed.threshold}+ (Greed/Extreme Greed), accumulation signals are downgraded because buying during euphoria often means buying near local tops.
          </p>
          <p style={{ margin: `${SPACE.sm}px 0 0`, fontSize: TYPE.caption, color: PALETTE.textMuted }}>
            Current: {value} ({classification}) | Threshold: ≥{fearGreed.threshold} triggers downgrade | {isGreedy ? '⚠️ Downgrade active' : '✓ No downgrade'}
          </p>
        </div>
      )}
    </div>
  );
}

function StrategySection({ isMobile }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
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
          width: '100%',
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
              <p style={{ margin: `0 0 ${SPACE.sm}px` }}>
                <strong style={{ color: PALETTE.textPrimary }}>Buying weakness in non-leaders = momentum trap.</strong> Without fundamental strength, oversold assets often continue declining.
              </p>
              <p style={{ margin: 0 }}>
                <strong style={{ color: PALETTE.textPrimary }}>Macro filters suppress accumulation</strong> when conditions are unfavorable: GLI contracting, asset underperforming BTC, or Fear & Greed in greed territory. When any filter is active, signals downgrade one level (strong-accumulate→accumulate, accumulate→hold).
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
              <div><span style={{ color: PALETTE.textSecondary }}>Wyckoff</span> — Phase filter (not in composite weight)</div>
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
                <span style={{ color: TIER_CONFIG['leader'].accent }}>Leaders</span> — Core positions for accumulation. Composite ≥75, clear institutional path, no existential regulatory risk.
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
              <div style={{ marginTop: `${SPACE.md}px`, paddingLeft: `${SPACE.md}px`, borderLeft: `2px solid #d49a6a` }}>
                <div style={{ color: '#d49a6a', marginBottom: '2px' }}>Downgrade Filters (OR logic)</div>
                When ANY of these conditions is true, signals downgrade one level (strong-accumulate→accumulate, accumulate→hold):<br/>
                • <strong>GLI contracting</strong> — Global Liquidity Index today &lt; 75 days ago<br/>
                • <strong>RS underperforming</strong> — Asset/BTC ratio declined ≥10% over 90 days<br/>
                • <strong>Fear & Greed ≥70</strong> — Market in greed/extreme greed territory
              </div>
              <p style={{ margin: `${SPACE.sm}px 0 0`, fontStyle: 'italic' }}>
                Additional filter: Weekly RSI falling from elevated levels (&gt;55, dropped &gt;8 points) downgrades strong-accumulate to accumulate only.
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
              <div><span style={{ color: PALETTE.textSecondary }}>Deliberate</span> — Weekly scoring, daily indicators</div>
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
  const [expanded, setExpanded] = useState(false);

  const items = [
    { key: 'strong-accumulate', text: 'Capitulation (weekly + daily RSI <30) or Wyckoff dip (Phase C+, daily RSI ≤32, weekly RSI ≥42). Downgrades to accumulate when any filter active: GLI contracting, RS underperforming BTC, or Fear & Greed ≥70.' },
    { key: 'accumulate', text: 'Weekly RSI <30 alone, or Wyckoff dip filtered by RSI slope. Downgrades to hold when any macro filter active (GLI, RS, or F&G).' },
    { key: 'promote', text: 'Runner-up crossing leader threshold. Composite ≥75 with 30-day trend ≥+8 and 7-day trend ≥+2.' },
    { key: 'hold', text: 'Active leader position. No accumulation signal. Patience by design — also the downgrade target when macro filters suppress accumulation.' },
    { key: 'await', text: 'Runner-up building signal. Monitoring for promotion criteria.' },
    { key: 'observe', text: 'Observation tier (composite 50-64). Research only, no position.' },
    { key: 'stand-aside', text: 'Distribution phase detected or sharp composite decline (≥5 pts/week). Capital preservation priority.' },
  ];

  return (
    <div>
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
          width: '100%',
        }}
      >
        <span style={{
          transition: 'transform 0.2s',
          display: 'inline-block',
          transform: expanded ? 'rotate(90deg)' : 'none',
        }}>▸</span>
        {expanded ? 'Hide signal reference' : 'Signal reference'}
      </button>

      {expanded && (
        <div style={{
          marginTop: `${SPACE.lg}px`,
          padding: `${SPACE.lg}px`,
          background: PALETTE.cardBg,
          border: `1px solid ${PALETTE.border}`,
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(280px, 1fr))', gap: `${SPACE.base}px` }}>
            {items.map(item => {
              const cfg = ACTION_CONFIG[item.key];
              return (
                <div key={item.key} style={{ display: 'flex', gap: `${SPACE.sm}px`, alignItems: 'flex-start' }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: cfg.dot === '#121110' ? cfg.bg : cfg.dot, marginTop: '6px', flexShrink: 0 }} />
                  <div style={{ fontSize: TYPE.small, color: PALETTE.textSecondary }}>
                    <span style={{ fontFamily: 'ui-monospace, monospace', fontSize: TYPE.caption, letterSpacing: '0.06em', textTransform: 'uppercase', color: PALETTE.textSecondary, fontWeight: 500 }}>
                      {cfg.label}
                    </span>
                    <span style={{ color: PALETTE.textMuted }}> — {item.text}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function RelativeStrengthSection({ assets, rs, isMobile }) {
  const [expanded, setExpanded] = useState(false);

  // Filter to assets with RS data (excluding BTC)
  const assetsWithRs = assets.filter(a => a.rs_vs_btc && a.symbol !== 'BTC' && a.rs_vs_btc.change_pct !== null);
  const total = assetsWithRs.length;

  // Don't render if RS is disabled or no data
  if (!rs || !rs.enabled || total === 0) return null;

  const lookbackDays = rs.lookback_days || 90;
  const threshold = rs.underperformance_threshold || 0.10;

  // Categorize assets
  const outperforming = assetsWithRs.filter(a => a.rs_vs_btc.change_pct >= threshold);
  const stable = assetsWithRs.filter(a => a.rs_vs_btc.change_pct > -threshold && a.rs_vs_btc.change_pct < threshold);
  const underperforming = assetsWithRs.filter(a => a.rs_vs_btc.change_pct <= -threshold);

  // Sort each category
  const sortedOutperforming = [...outperforming].sort((a, b) => (b.rs_vs_btc.change_pct || 0) - (a.rs_vs_btc.change_pct || 0));
  const sortedStable = [...stable].sort((a, b) => (b.rs_vs_btc.change_pct || 0) - (a.rs_vs_btc.change_pct || 0));
  const sortedUnderperforming = [...underperforming].sort((a, b) => (a.rs_vs_btc.change_pct || 0) - (b.rs_vs_btc.change_pct || 0));

  const RsAssetRow = ({ asset, type }) => {
    const changePct = asset.rs_vs_btc.change_pct || 0;
    const tierConfig = TIER_CONFIG[asset.tier];
    const color = type === 'outperforming' ? '#7aa872' : type === 'underperforming' ? '#c89678' : PALETTE.textMuted;
    const Icon = type === 'outperforming' ? TrendingUp : type === 'underperforming' ? TrendingDown : Minus;

    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: `${SPACE.sm}px`,
        padding: `${SPACE.sm}px ${SPACE.md}px`,
        background: PALETTE.cardInset,
      }}>
        <span style={{
          fontFamily: 'Georgia, serif',
          fontSize: TYPE.body,
          color: PALETTE.textPrimary,
          minWidth: '60px',
        }}>
          {asset.symbol}
        </span>
        <span style={{
          fontSize: TYPE.caption,
          color: tierConfig?.accent || PALETTE.textMuted,
          fontFamily: 'ui-monospace, monospace',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
          opacity: 0.7,
        }}>
          {asset.tier}
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: TYPE.small,
          color: color,
          fontFamily: 'ui-monospace, monospace',
          display: 'flex',
          alignItems: 'center',
          gap: '3px',
        }}>
          <Icon size={12} strokeWidth={2} />
          {changePct >= 0 ? '+' : ''}{(changePct * 100).toFixed(0)}%
        </span>
      </div>
    );
  };

  const CategorySection = ({ title, items, type, color }) => {
    if (items.length === 0) return null;
    return (
      <div style={{ marginBottom: `${SPACE.lg}px` }}>
        <div style={{
          fontSize: TYPE.caption,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: color,
          fontFamily: 'ui-monospace, monospace',
          marginBottom: `${SPACE.sm}px`,
          display: 'flex',
          alignItems: 'center',
          gap: `${SPACE.sm}px`,
        }}>
          {title} — {items.length}
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: `${SPACE.sm}px`,
        }}>
          {items.map(asset => <RsAssetRow key={asset.symbol} asset={asset} type={type} />)}
        </div>
      </div>
    );
  };

  return (
    <div>
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
          width: '100%',
        }}
      >
        <span style={{
          transition: 'transform 0.2s',
          display: 'inline-block',
          transform: expanded ? 'rotate(90deg)' : 'none',
        }}>▸</span>
        <span>Relative Strength vs BTC ({lookbackDays}d):</span>
        <span style={{ color: '#7aa872' }}>{outperforming.length}↑</span>
        <span style={{ color: PALETTE.textMuted }}>{stable.length}—</span>
        <span style={{ color: '#c89678' }}>{underperforming.length}↓</span>
      </button>

      {expanded && (
        <div style={{
          marginTop: `${SPACE.lg}px`,
          padding: `${SPACE.lg}px`,
          background: PALETTE.cardBg,
          border: `1px solid ${PALETTE.border}`,
        }}>
          <CategorySection title="Outperforming" items={sortedOutperforming} type="outperforming" color="#7aa872" />
          <CategorySection title="Stable" items={sortedStable} type="stable" color={PALETTE.textMuted} />
          <CategorySection title="Underperforming" items={sortedUnderperforming} type="underperforming" color="#c89678" />

          <div style={{
            marginTop: `${SPACE.sm}px`,
            fontSize: TYPE.caption,
            color: PALETTE.textMuted,
            fontFamily: 'ui-monospace, monospace',
            fontStyle: 'italic',
          }}>
            Threshold: ±{(threshold * 100).toFixed(0)}%. Underperforming assets have strong-accumulate signals suppressed.
          </div>
        </div>
      )}
    </div>
  );
}

function TierSection({ tier, assets, isMobile, defaultExpanded = false, gli, rs, fearGreed }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const config = TIER_CONFIG[tier];
  if (!config) return null;

  const count = assets.length;

  return (
    <div style={{ marginBottom: `${SPACE.xl}px` }}>
      <button
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        style={{
          background: 'transparent',
          border: 'none',
          color: config.accent,
          padding: 0,
          fontSize: TYPE.small,
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
          fontFamily: 'ui-monospace, monospace',
          fontWeight: 500,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: `${SPACE.md}px`,
          width: '100%',
          textAlign: 'left',
          minHeight: isMobile ? '44px' : 'auto',
        }}
      >
        <div style={{ width: `${SPACE.xl}px`, height: '1px', background: config.accent }} />
        <span style={{
          transition: 'transform 0.2s',
          display: 'inline-block',
          transform: expanded ? 'rotate(90deg)' : 'none',
          fontSize: TYPE.caption,
        }}>▸</span>
        <span>{config.label} — {count}</span>
      </button>

      {expanded && (
        <div style={{ marginTop: `${SPACE.lg}px` }}>
          {count === 0 ? (
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
              {assets.map(asset => (
                <ScoreCard key={asset.symbol} asset={asset} isMobile={isMobile} gli={gli} rs={rs} fearGreed={fearGreed} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
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
  const [rs, setRs] = useState(null); // Relative Strength vs BTC status
  const [fearGreed, setFearGreed] = useState(null); // Fear & Greed Index status
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
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
        // Load weight profiles from backend (overrides defaults)
        if (data.weight_profiles) {
          setWeightProfiles(data.weight_profiles);
        }
        // Load GLI (Global Liquidity Index) status
        if (data.gli) {
          setGli(data.gli);
        }
        // Load RS (Relative Strength vs BTC) status
        if (data.rs) {
          setRs(data.rs);
        }
        // Load Fear & Greed Index status
        if (data.fear_greed) {
          setFearGreed(data.fear_greed);
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

    return [...qualified].sort((a, b) => {
      const aStrong = a.action === 'strong-accumulate' ? 0 : 1;
      const bStrong = b.action === 'strong-accumulate' ? 0 : 1;
      const tierDiff = (TIER_CONFIG[a.tier]?.order || 0) - (TIER_CONFIG[b.tier]?.order || 0);
      if (tierDiff !== 0) return tierDiff;
      if (aStrong !== bStrong) return aStrong - bStrong;
      return (b.composite || 0) - (a.composite || 0);
    });
  }, [assets, thresholds.min_display_score]);

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
      {/* Header: title + timestamp + description */}
      <div style={{ maxWidth: '900px', margin: `0 auto ${SPACE.lg}px` }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', flexWrap: 'wrap', gap: `${SPACE.sm}px`, marginBottom: `${SPACE.sm}px` }}>
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
          </div>
        </div>
        <div style={{
          fontSize: TYPE.small,
          color: PALETTE.textSecondary,
          fontFamily: 'Georgia, serif',
          lineHeight: TYPE.relaxed,
        }}>
          Fundamentals identify <em>what</em> to buy, technicals determine <em>when</em>.
        </div>
      </div>

      <ActionSummary assets={assets} isMobile={isMobile} minScore={thresholds.min_display_score} strongCount={strongCount} gli={gli} rs={rs} />

      <div style={{ maxWidth: '900px', margin: '0 auto' }}>
        {['leader', 'runner-up', 'observation'].map(tier => {
          const tierAssets = groupedAssets[tier];
          // Skip tier if no assets
          if (tierAssets.length === 0) return null;

          return (
            <TierSection
              key={tier}
              tier={tier}
              assets={tierAssets}
              isMobile={isMobile}
              defaultExpanded={tier === 'leader'}
              gli={gli}
              rs={rs}
              fearGreed={fearGreed}
            />
          );
        })}
      </div>

      {/* Footer with reference info */}
      <div style={{ maxWidth: '900px', margin: `${isMobile ? SPACE['2xl'] : SPACE['3xl']}px auto 0`, borderTop: `1px solid ${PALETTE.border}`, paddingTop: `${SPACE.lg}px`, display: 'flex', flexDirection: 'column', gap: `${SPACE.md}px` }}>
        <GliSection gli={gli} isMobile={isMobile} />
        <FearGreedSection fearGreed={fearGreed} isMobile={isMobile} />
        <RelativeStrengthSection assets={assets} rs={rs} isMobile={isMobile} />
        <StrategySection isMobile={isMobile} />
        <ActionLegend isMobile={isMobile} />
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<Dashboard />);
