(() => {
  const { useState, useEffect, useMemo } = React;
  const BREAKPOINTS = {
    mobile: 480,
    tablet: 768,
    desktop: 1024
  };
  function useIsMobile() {
    const [isMobile, setIsMobile] = useState(window.innerWidth < BREAKPOINTS.tablet);
    useEffect(() => {
      const handler = () => setIsMobile(window.innerWidth < BREAKPOINTS.tablet);
      window.addEventListener("resize", handler);
      return () => window.removeEventListener("resize", handler);
    }, []);
    return isMobile;
  }
  const Icon = ({ children, size = 24, color = "currentColor", strokeWidth = 2, fill = "none", ...props }) => /* @__PURE__ */ React.createElement("svg", { width: size, height: size, viewBox: "0 0 24 24", fill, stroke: color, strokeWidth, strokeLinecap: "round", strokeLinejoin: "round", ...props }, children);
  const TrendingUp = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("polyline", { points: "23 6 13.5 15.5 8.5 10.5 1 18" }), /* @__PURE__ */ React.createElement("polyline", { points: "17 6 23 6 23 12" }));
  const TrendingDown = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("polyline", { points: "23 18 13.5 8.5 8.5 13.5 1 6" }), /* @__PURE__ */ React.createElement("polyline", { points: "17 18 23 18 23 12" }));
  const Minus = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("line", { x1: "5", y1: "12", x2: "19", y2: "12" }));
  const CheckCircle2 = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("circle", { cx: "12", cy: "12", r: "10" }), /* @__PURE__ */ React.createElement("path", { d: "m9 12 2 2 4-4" }));
  const Clock = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("circle", { cx: "12", cy: "12", r: "10" }), /* @__PURE__ */ React.createElement("polyline", { points: "12 6 12 12 16 14" }));
  const Eye = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("path", { d: "M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" }), /* @__PURE__ */ React.createElement("circle", { cx: "12", cy: "12", r: "3" }));
  const ArrowUpCircle = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("circle", { cx: "12", cy: "12", r: "10" }), /* @__PURE__ */ React.createElement("polyline", { points: "16 12 12 8 8 12" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "16", x2: "12", y2: "8" }));
  const Zap = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("polygon", { points: "13 2 3 14 12 14 11 22 21 10 12 10 13 2" }));
  const AlertCircle = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("circle", { cx: "12", cy: "12", r: "10" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "8", x2: "12", y2: "12" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "16", x2: "12.01", y2: "16" }));
  const Loader2 = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("path", { d: "M21 12a9 9 0 1 1-6.219-8.56" }));
  const X = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("line", { x1: "18", y1: "6", x2: "6", y2: "18" }), /* @__PURE__ */ React.createElement("line", { x1: "6", y1: "6", x2: "18", y2: "18" }));
  const Info = (props) => /* @__PURE__ */ React.createElement(Icon, { ...props }, /* @__PURE__ */ React.createElement("circle", { cx: "12", cy: "12", r: "10" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "16", x2: "12", y2: "12" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "8", x2: "12.01", y2: "8" }));
  const WEIGHTS_BY_TYPE = {
    "store-of-value": { institutional: 0.4, supply: 0.25, regulatory: 0.15, wyckoff: 0.15, revenue: 0.05 },
    "smart-contract": { institutional: 0.3, revenue: 0.25, supply: 0.2, regulatory: 0.15, wyckoff: 0.1 },
    "defi": { revenue: 0.35, institutional: 0.25, regulatory: 0.2, supply: 0.15, wyckoff: 0.05 },
    "infrastructure": { institutional: 0.35, regulatory: 0.25, supply: 0.2, revenue: 0.1, wyckoff: 0.1 }
  };
  const DEFAULT_WEIGHTS = { institutional: 0.3, revenue: 0.2, regulatory: 0.2, supply: 0.2, wyckoff: 0.1 };
  function getWeights(assetType) {
    return WEIGHTS_BY_TYPE[assetType] || DEFAULT_WEIGHTS;
  }
  const PALETTE = {
    bg: "#121110",
    cardBg: "#1a1816",
    cardInset: "#211e1b",
    border: "#3a342d",
    borderStrong: "#55493c",
    textPrimary: "#ede7d9",
    textSecondary: "#a39a8a",
    textMuted: "#958b7b",
    // Was #6e665a (3.1:1) → now 4.6:1 contrast
    trackBg: "#2a2620"
  };
  const SPACE = {
    xs: 4,
    sm: 8,
    md: 12,
    base: 16,
    lg: 24,
    xl: 32,
    "2xl": 48,
    "3xl": 64,
    "4xl": 96
  };
  const TYPE = {
    // Sizes
    caption: "0.75rem",
    // 12px - minimum for labels
    small: "0.8125rem",
    // 13px - secondary text
    body: "0.875rem",
    // 14px - body copy
    base: "1rem",
    // 16px - emphasized body
    subhead: "1.125rem",
    // 18px - subheadings
    heading: "1.5rem",
    // 24px - card headings
    title: "2rem",
    // 32px - page title
    display: "2.5rem",
    // 40px - large numbers (mobile)
    displayLg: "3rem",
    // 48px - large numbers (desktop)
    // Line heights
    tight: 1.1,
    snug: 1.25,
    normal: 1.5,
    relaxed: 1.65
  };
  const DIMENSION_LABELS = {
    institutional: "Institutional",
    revenue: "Revenue/Fees",
    regulatory: "Regulatory",
    supply: "Supply/On-Chain",
    wyckoff: "Wyckoff"
  };
  const ASSET_TYPE_LABELS = {
    "store-of-value": "Store of Value",
    "smart-contract": "Smart Contract",
    "defi": "DeFi",
    "infrastructure": "Infrastructure"
  };
  const TIER_CONFIG = {
    "leader": { label: "Leaders", icon: CheckCircle2, accent: "#5aafcf", order: 0 },
    "runner-up": { label: "Runner-ups", icon: Clock, accent: "#6a9a90", order: 1 },
    "observation": { label: "Observation", icon: Eye, accent: "#8a8a9a", order: 2 }
  };
  const ACTION_CONFIG = {
    "strong-accumulate": { label: "Strong Accumulate", desc: "Dislocation in accumulation zone", bg: "#4ac0e0", fg: "#0a1a20", dot: "#0a1a20", icon: Zap, emphatic: true },
    "accumulate": { label: "Accumulate", desc: "Tranche-eligible zone", bg: "#5aafcf", fg: "#0a1820", dot: "#0a1820" },
    "promote": { label: "Promote Candidate", desc: "Runner-up earning activation", bg: "#1a3038", fg: "#8ad0e8", dot: "#5aafcf", icon: ArrowUpCircle },
    "hold": { label: "Hold & Monitor", desc: "Position active, no action", bg: "transparent", fg: "#6a9a90", dot: "#6a9a90", border: true },
    "await": { label: "Await Confirmation", desc: "Signal building, not yet", bg: "transparent", fg: "#9a9085", dot: "#9a9085", border: true },
    "observe": { label: "Observe", desc: "Scanning only", bg: "transparent", fg: "#8a8a9a", dot: "#8a8a9a", border: true },
    "stand-aside": { label: "Stand Aside", desc: "Do not engage", bg: "transparent", fg: "#d06868", dot: "#d06868", border: true }
  };
  function computeComposite(scores, assetType) {
    const weights = getWeights(assetType);
    let total = 0;
    let totalWeight = 0;
    let missingCount = 0;
    for (const [dim, weight] of Object.entries(weights)) {
      const score = scores[dim];
      if (score !== null && score !== void 0 && !isNaN(score)) {
        total += score * weight;
        totalWeight += weight;
      } else {
        missingCount += 1;
      }
    }
    const composite = totalWeight > 0 ? Math.round(total / totalWeight) : 50;
    return { composite, missingCount };
  }
  function weeklyDelta(trend) {
    if (!trend || trend.length < 2) return 0;
    const first = trend[0];
    const last = trend[trend.length - 1];
    if (typeof first !== "number" || typeof last !== "number" || isNaN(first) || isNaN(last)) return 0;
    return last - first;
  }
  function monthlyDelta(trend30d) {
    if (!trend30d || trend30d.length < 2) return 0;
    const first = trend30d[0];
    const last = trend30d[trend30d.length - 1];
    if (typeof first !== "number" || typeof last !== "number" || isNaN(first) || isNaN(last)) return 0;
    return last - first;
  }
  function relativeTime(dateStr) {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    const now = /* @__PURE__ */ new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 6e4);
    const diffHours = Math.floor(diffMs / 36e5);
    const diffDays = Math.floor(diffMs / 864e5);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }
  function isStale(dateStr) {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    const now = /* @__PURE__ */ new Date();
    const diffHours = (now - date) / 36e5;
    return diffHours > 25;
  }
  function Sparkline({ data, accent }) {
    if (!data || data.length < 2) return null;
    const validData = data.filter((v) => typeof v === "number" && !isNaN(v));
    if (validData.length < 2) return null;
    const min = Math.min(...validData);
    const max = Math.max(...validData);
    const range = max - min || 1;
    const width = 80;
    const height = 24;
    const points = validData.map((v, i) => {
      const x = i / (validData.length - 1) * width;
      const y = height - (v - min) / range * height;
      return `${x},${y}`;
    }).join(" ");
    return /* @__PURE__ */ React.createElement("svg", { width, height, style: { display: "block" } }, /* @__PURE__ */ React.createElement("polyline", { points, fill: "none", stroke: accent, strokeWidth: "1.5", strokeLinecap: "round", strokeLinejoin: "round" }));
  }
  function DimensionBar({ label, value, accent, weight }) {
    const isMissing = value === null || value === void 0 || typeof value === "number" && isNaN(value);
    const displayValue = isMissing ? "N/A" : value;
    const barColor = isMissing ? "#4a4035" : accent;
    return /* @__PURE__ */ React.createElement("div", { style: { marginBottom: `${SPACE.md}px`, opacity: isMissing ? 0.6 : 1 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: TYPE.caption, letterSpacing: "0.05em", textTransform: "uppercase", color: PALETTE.textMuted, marginBottom: `${SPACE.xs}px`, fontFamily: "ui-monospace, monospace" } }, /* @__PURE__ */ React.createElement("span", { style: { display: "flex", alignItems: "center", gap: "4px" } }, label, weight && !isMissing && /* @__PURE__ */ React.createElement("span", { style: { opacity: 0.6, marginLeft: `${SPACE.xs}px` } }, "(", Math.round(weight * 100), "%)"), isMissing && /* @__PURE__ */ React.createElement("span", { style: { opacity: 0.6, marginLeft: `${SPACE.xs}px` } }, "(excluded)")), /* @__PURE__ */ React.createElement("span", { style: {
      color: isMissing ? "#d49a6a" : PALETTE.textPrimary,
      display: "flex",
      alignItems: "center",
      gap: "4px"
    } }, isMissing && /* @__PURE__ */ React.createElement(AlertCircle, { size: 10, color: "#d49a6a", strokeWidth: 2 }), displayValue)), /* @__PURE__ */ React.createElement("div", { style: { height: "3px", background: PALETTE.trackBg, overflow: "hidden" } }, isMissing ? /* @__PURE__ */ React.createElement("div", { style: {
      height: "100%",
      width: "100%",
      background: `repeating-linear-gradient(90deg, ${barColor} 0px, ${barColor} 4px, transparent 4px, transparent 8px)`
    } }) : /* @__PURE__ */ React.createElement("div", { style: {
      height: "100%",
      width: "100%",
      background: accent,
      transformOrigin: "left",
      transform: `scaleX(${value / 100})`,
      transition: "transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)"
    } })));
  }
  function rsiColor(rsi) {
    if (rsi === null || rsi === void 0) return PALETTE.textMuted;
    if (rsi >= 75) return "#d47878";
    if (rsi >= 70) return "#d49a6a";
    if (rsi < 25) return "#7aa0c4";
    if (rsi <= 32) return "#8ab0d4";
    return PALETTE.textPrimary;
  }
  function rsiLabel(rsi) {
    if (rsi === null || rsi === void 0) return "n/a";
    if (rsi >= 75) return "Overbought";
    if (rsi >= 70) return "Elevated";
    if (rsi < 25) return "Deep oversold";
    if (rsi <= 32) return "Oversold";
    return "Neutral";
  }
  function RsiRow({ asset }) {
    const { rsi_daily, rsi_weekly } = asset;
    const Cell = ({ label, value }) => /* @__PURE__ */ React.createElement("div", { style: { flex: 1, textAlign: "center", padding: `${SPACE.sm}px ${SPACE.sm}px`, background: PALETTE.cardInset } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.caption, letterSpacing: "0.08em", textTransform: "uppercase", color: PALETTE.textMuted, fontFamily: "ui-monospace, monospace", marginBottom: `${SPACE.xs}px` } }, label), /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "Georgia, serif", fontSize: TYPE.subhead, fontWeight: 400, color: rsiColor(value), lineHeight: 1 } }, value === null || value === void 0 ? "\u2014" : value), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.caption, color: rsiColor(value), fontFamily: "ui-monospace, monospace", letterSpacing: "0.04em", marginTop: `${SPACE.xs}px`, fontStyle: "italic", opacity: 0.85 } }, rsiLabel(value)));
    return /* @__PURE__ */ React.createElement("div", { style: { marginBottom: `${SPACE.base}px` } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.caption, letterSpacing: "0.08em", textTransform: "uppercase", color: PALETTE.textMuted, marginBottom: `${SPACE.sm}px`, fontFamily: "ui-monospace, monospace" } }, "RSI \xB7 14"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: `${SPACE.sm}px` } }, /* @__PURE__ */ React.createElement(Cell, { label: "Daily", value: rsi_daily }), /* @__PURE__ */ React.createElement(Cell, { label: "Weekly", value: rsi_weekly })));
  }
  function getActionReasoning(asset) {
    const action = asset.action || "observe";
    const composite = asset.composite || 50;
    const delta = weeklyDelta(asset.trend);
    const delta30 = monthlyDelta(asset.trend_30d);
    const rsiDaily = asset.rsi_daily;
    const rsiWeekly = asset.rsi_weekly;
    switch (action) {
      case "strong-accumulate":
        return `Daily RSI at ${rsiDaily} signals short-term oversold while weekly RSI (${rsiWeekly}) and composite (${composite}) remain healthy. This dislocation within an accumulation zone is a high-conviction entry point.`;
      case "accumulate":
        return `Composite score of ${composite} with ${delta >= 0 ? "stable" : "minor pullback"} trend. RSI levels support accumulation. Leader-tier asset in favorable Wyckoff phase for tranche building.`;
      case "promote":
        return `Runner-up crossing leader threshold with composite at ${composite}${delta30 > 0 ? ` and +${delta30}-point 30-day momentum` : ""}. Evaluate for potential tier promotion.`;
      case "hold":
        return `Position active with composite at ${composite}. No accumulate or trim signals present. Current allocation appropriate \u2014 patience is the strategy.`;
      case "await":
        return `Signal building but not yet confirmed. Composite at ${composite}${delta > 0 ? ` with ${delta}-point uptick` : ""}. Monitor for entry criteria before activation.`;
      case "observe":
        return `Observation tier \u2014 scanning only. ${composite >= 70 ? "Composite healthy but" : "Composite at " + composite + ","} no position warranted at this time.`;
      case "stand-aside":
        return `Distribution risk detected${delta < -3 ? ` with ${Math.abs(delta)}-point weekly decline` : ""}${rsiWeekly >= 70 ? ` and elevated weekly RSI (${rsiWeekly})` : ""}. Do not engage regardless of price action.`;
      default:
        return null;
    }
  }
  function DetailModal({ asset, onClose, isMobile }) {
    useEffect(() => {
      const handleEsc = (e) => {
        if (e.key === "Escape") onClose();
      };
      window.addEventListener("keydown", handleEsc);
      return () => window.removeEventListener("keydown", handleEsc);
    }, [onClose]);
    useEffect(() => {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }, []);
    const config = TIER_CONFIG[asset.tier];
    const TierIcon = config?.icon || Eye;
    return /* @__PURE__ */ React.createElement(
      "div",
      {
        onClick: onClose,
        style: {
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0, 0, 0, 0.85)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1e3,
          padding: isMobile ? SPACE.base : SPACE.xl
        }
      },
      /* @__PURE__ */ React.createElement(
        "div",
        {
          onClick: (e) => e.stopPropagation(),
          style: {
            background: PALETTE.cardBg,
            border: `1px solid ${PALETTE.borderStrong}`,
            maxWidth: "640px",
            width: "100%",
            maxHeight: "90vh",
            overflow: "auto",
            position: "relative"
          }
        },
        /* @__PURE__ */ React.createElement("div", { style: {
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          padding: isMobile ? SPACE.base : SPACE.lg,
          borderBottom: `1px solid ${PALETTE.border}`,
          position: "sticky",
          top: 0,
          background: PALETTE.cardBg,
          zIndex: 1
        } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: SPACE.sm } }, /* @__PURE__ */ React.createElement("span", { style: { fontFamily: "Georgia, serif", fontSize: isMobile ? TYPE.heading : "1.625rem", fontWeight: 400, color: PALETTE.textPrimary } }, asset.symbol), /* @__PURE__ */ React.createElement(TierIcon, { size: 16, color: config?.accent || PALETTE.textMuted, strokeWidth: 1.5 })), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.small, letterSpacing: "0.08em", textTransform: "uppercase", color: PALETTE.textSecondary, marginTop: SPACE.xs, fontFamily: "ui-monospace, monospace" } }, asset.name, " \xB7 ", ASSET_TYPE_LABELS[asset.asset_type] || asset.asset_type)), /* @__PURE__ */ React.createElement(
          "button",
          {
            onClick: onClose,
            style: {
              background: "transparent",
              border: "none",
              color: PALETTE.textMuted,
              cursor: "pointer",
              padding: SPACE.sm,
              marginRight: -SPACE.sm,
              marginTop: -SPACE.xs
            },
            "aria-label": "Close"
          },
          /* @__PURE__ */ React.createElement(X, { size: 20, strokeWidth: 1.5 })
        )),
        /* @__PURE__ */ React.createElement("div", { style: { padding: isMobile ? SPACE.base : SPACE.lg } }, /* @__PURE__ */ React.createElement("div", { style: {
          display: "inline-flex",
          alignItems: "center",
          gap: SPACE.sm,
          padding: `${SPACE.sm}px ${SPACE.base}px`,
          background: PALETTE.cardInset,
          marginBottom: SPACE.lg
        } }, /* @__PURE__ */ React.createElement("span", { style: { fontFamily: "Georgia, serif", fontSize: TYPE.heading, fontWeight: 300, color: PALETTE.textPrimary } }, asset.composite), /* @__PURE__ */ React.createElement("span", { style: { fontSize: TYPE.caption, letterSpacing: "0.08em", textTransform: "uppercase", color: PALETTE.textMuted, fontFamily: "ui-monospace, monospace" } }, "Composite")), /* @__PURE__ */ React.createElement("div", { style: {
          fontFamily: "Georgia, serif",
          fontSize: TYPE.body,
          lineHeight: TYPE.relaxed,
          color: PALETTE.textSecondary,
          whiteSpace: "pre-wrap"
        } }, asset.note_detailed || asset.note || "No detailed analysis available.")),
        /* @__PURE__ */ React.createElement("div", { style: {
          padding: isMobile ? SPACE.base : SPACE.lg,
          borderTop: `1px solid ${PALETTE.border}`,
          background: PALETTE.cardInset
        } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.caption, letterSpacing: "0.06em", color: PALETTE.textMuted, fontFamily: "ui-monospace, monospace" } }, asset.wyckoff_phase, " \xB7 Last updated: ", (/* @__PURE__ */ new Date()).toLocaleDateString()))
      )
    );
  }
  function ActionBanner({ action, daysAgo, strongDays }) {
    const cfg = ACTION_CONFIG[action];
    if (!cfg) return null;
    const recentChange = daysAgo <= 14;
    const Icon2 = cfg.icon;
    const isStrong = action === "strong-accumulate";
    return /* @__PURE__ */ React.createElement("div", { style: {
      background: cfg.bg,
      color: cfg.fg,
      border: cfg.border ? `1px solid ${cfg.dot}` : "none",
      padding: `${SPACE.md}px ${SPACE.base}px`,
      marginBottom: `${SPACE.base}px`,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: `${SPACE.sm}px`,
      boxShadow: isStrong ? `0 0 0 2px ${PALETTE.bg}, 0 0 0 3px #4ac0e0` : "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: `${SPACE.sm}px` } }, Icon2 ? /* @__PURE__ */ React.createElement(Icon2, { size: isStrong ? 16 : 14, color: cfg.dot, strokeWidth: 1.75, fill: isStrong ? cfg.dot : "none" }) : /* @__PURE__ */ React.createElement("div", { style: { width: "6px", height: "6px", borderRadius: "50%", background: cfg.dot, flexShrink: 0 } }), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.small, letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "ui-monospace, monospace", fontWeight: isStrong ? 700 : 500 } }, cfg.label), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.caption, letterSpacing: "0.04em", opacity: 0.8, fontFamily: "ui-monospace, monospace", marginTop: "2px" } }, cfg.desc))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.caption, letterSpacing: "0.06em", fontFamily: "ui-monospace, monospace", textAlign: "right", lineHeight: 1.3, opacity: recentChange ? 1 : 0.7 } }, isStrong && strongDays > 1 ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { fontWeight: 600, marginBottom: "1px" } }, "DAY ", strongDays), /* @__PURE__ */ React.createElement("div", { style: { opacity: 0.7 } }, "continuation")) : isStrong && strongDays === 1 ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { fontWeight: 700, marginBottom: "1px" } }, "NEW"), /* @__PURE__ */ React.createElement("div", null, "today")) : /* @__PURE__ */ React.createElement(React.Fragment, null, recentChange && /* @__PURE__ */ React.createElement("div", { style: { fontWeight: 600, marginBottom: "1px" } }, "NEW"), /* @__PURE__ */ React.createElement("div", null, daysAgo || 0, "d"))));
  }
  function ScoreCard({ asset, isMobile }) {
    const [showAllDimensions, setShowAllDimensions] = useState(false);
    const [showDetail, setShowDetail] = useState(false);
    const assetType = asset.asset_type || "smart-contract";
    const weights = asset.weights || getWeights(assetType);
    let composite, missingDimensions;
    if (asset.composite !== void 0) {
      composite = asset.composite;
      missingDimensions = asset.missing_dimensions || 0;
    } else {
      const computed = computeComposite(asset.scores, assetType);
      composite = computed.composite;
      missingDimensions = computed.missingCount;
    }
    const delta = weeklyDelta(asset.trend);
    const config = TIER_CONFIG[asset.tier];
    if (!config) return null;
    const hasIncompleteData = missingDimensions > 0;
    const Icon2 = config.icon;
    const action = asset.action || "observe";
    const isStrong = action === "strong-accumulate";
    const deltaColor = delta > 0 ? "#7aa872" : delta < 0 ? "#c27878" : PALETTE.textMuted;
    const DeltaIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;
    const sortedDimensions = Object.entries(weights).sort(([, a], [, b]) => b - a).map(([key]) => key);
    const visibleDimensions = showAllDimensions ? sortedDimensions : sortedDimensions.slice(0, 3);
    const hiddenCount = sortedDimensions.length - 3;
    return /* @__PURE__ */ React.createElement("div", { style: {
      background: PALETTE.cardBg,
      border: isStrong ? `1px solid #4ac0e0` : `1px solid ${PALETTE.borderStrong}`,
      padding: isMobile ? `${SPACE.base}px` : `${SPACE.lg}px`,
      display: "flex",
      flexDirection: "column"
    } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: `${SPACE.base}px` } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "Georgia, serif", fontSize: isMobile ? TYPE.heading : "1.625rem", fontWeight: 400, color: PALETTE.textPrimary, lineHeight: 1 } }, asset.symbol), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.caption, letterSpacing: "0.08em", textTransform: "uppercase", color: PALETTE.textSecondary, marginTop: `${SPACE.xs}px`, fontFamily: "ui-monospace, monospace" } }, asset.name), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.caption, letterSpacing: "0.06em", textTransform: "uppercase", color: PALETTE.textMuted, marginTop: `${SPACE.xs}px`, fontFamily: "ui-monospace, monospace" } }, ASSET_TYPE_LABELS[assetType] || assetType)), /* @__PURE__ */ React.createElement(Icon2, { size: 16, color: config.accent, strokeWidth: 1.5 })), /* @__PURE__ */ React.createElement(ActionBanner, { action, daysAgo: asset.label_changed_days_ago, strongDays: asset.strong_accumulate_days_active }), /* @__PURE__ */ React.createElement("div", { style: {
      fontSize: TYPE.small,
      color: PALETTE.textSecondary,
      fontFamily: "Georgia, serif",
      fontStyle: "italic",
      lineHeight: TYPE.normal,
      marginBottom: `${SPACE.lg}px`,
      paddingLeft: `${SPACE.sm}px`,
      borderLeft: `2px solid ${PALETTE.border}`
    } }, getActionReasoning(asset)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: `${SPACE.md}px`, marginBottom: `${SPACE.xs}px`, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "Georgia, serif", fontSize: isMobile ? TYPE.display : TYPE.displayLg, fontWeight: 300, color: PALETTE.textPrimary, lineHeight: 1, letterSpacing: "-0.02em" } }, composite), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: "3px", color: deltaColor, fontSize: TYPE.small, fontFamily: "ui-monospace, monospace" } }, /* @__PURE__ */ React.createElement(DeltaIcon, { size: 12, strokeWidth: 2 }), /* @__PURE__ */ React.createElement("span", null, delta > 0 ? "+" : "", delta)), /* @__PURE__ */ React.createElement("div", { style: { marginLeft: "auto" } }, /* @__PURE__ */ React.createElement(Sparkline, { data: asset.trend, accent: config.accent }))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: `${SPACE.sm}px`, fontSize: TYPE.caption, letterSpacing: "0.08em", textTransform: "uppercase", color: PALETTE.textMuted, marginBottom: `${SPACE.lg}px`, fontFamily: "ui-monospace, monospace" } }, /* @__PURE__ */ React.createElement("span", null, "Composite \xB7 7d"), hasIncompleteData && /* @__PURE__ */ React.createElement("span", { style: {
      display: "inline-flex",
      alignItems: "center",
      gap: "3px",
      padding: "2px 6px",
      background: "#3d2a1a",
      border: "1px solid #d49a6a",
      color: "#d49a6a",
      fontSize: TYPE.caption,
      letterSpacing: "0.06em"
    } }, /* @__PURE__ */ React.createElement(AlertCircle, { size: 10, color: "#d49a6a", strokeWidth: 2 }), missingDimensions, " dim. missing")), /* @__PURE__ */ React.createElement("div", { style: { marginBottom: `${SPACE.base}px` } }, visibleDimensions.map((dim) => /* @__PURE__ */ React.createElement(
      DimensionBar,
      {
        key: dim,
        label: DIMENSION_LABELS[dim],
        value: asset.scores[dim],
        accent: config.accent,
        weight: weights[dim]
      }
    )), hiddenCount > 0 && !showAllDimensions && /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setShowAllDimensions(true),
        style: {
          background: "transparent",
          border: "none",
          color: PALETTE.textSecondary,
          fontSize: TYPE.caption,
          fontFamily: "ui-monospace, monospace",
          letterSpacing: "0.06em",
          cursor: "pointer",
          padding: isMobile ? "12px 0" : "4px 0",
          minHeight: isMobile ? "44px" : "auto",
          opacity: 0.8
        }
      },
      "+",
      hiddenCount,
      " more"
    ), showAllDimensions && /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setShowAllDimensions(false),
        style: {
          background: "transparent",
          border: "none",
          color: PALETTE.textSecondary,
          fontSize: TYPE.caption,
          fontFamily: "ui-monospace, monospace",
          letterSpacing: "0.06em",
          cursor: "pointer",
          padding: isMobile ? "12px 0" : "4px 0",
          minHeight: isMobile ? "44px" : "auto",
          opacity: 0.8
        }
      },
      "Show less"
    )), /* @__PURE__ */ React.createElement(RsiRow, { asset }), /* @__PURE__ */ React.createElement("div", { style: { borderTop: `1px solid ${PALETTE.border}`, paddingTop: `${SPACE.md}px`, marginTop: "auto" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.caption, letterSpacing: "0.08em", textTransform: "uppercase", color: PALETTE.textMuted, marginBottom: `${SPACE.xs}px`, fontFamily: "ui-monospace, monospace" } }, asset.wyckoff_phase), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.small, color: PALETTE.textSecondary, fontStyle: "italic", fontFamily: "Georgia, serif", lineHeight: TYPE.normal } }, asset.note), asset.note_detailed && /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setShowDetail(true),
        style: {
          background: "transparent",
          border: "none",
          color: config.accent,
          fontSize: TYPE.caption,
          fontFamily: "ui-monospace, monospace",
          letterSpacing: "0.06em",
          cursor: "pointer",
          padding: isMobile ? `${SPACE.md}px 0` : `${SPACE.sm}px 0`,
          minHeight: isMobile ? "44px" : "auto",
          display: "flex",
          alignItems: "center",
          gap: `${SPACE.xs}px`,
          marginTop: `${SPACE.sm}px`
        }
      },
      /* @__PURE__ */ React.createElement(Info, { size: 12, strokeWidth: 1.5 }),
      "View details"
    )), showDetail && /* @__PURE__ */ React.createElement(
      DetailModal,
      {
        asset,
        onClose: () => setShowDetail(false),
        isMobile
      }
    ));
  }
  function ActionLegend({ isMobile }) {
    const items = [
      { key: "strong-accumulate", text: "Dislocation inside accumulation zone. Daily RSI \u226432, weekly \u226542, composite stable WoW. Shows day-counter when firing consecutively." },
      { key: "accumulate", text: "Tranche-eligible. Leader, composite \u226575, Wyckoff Phase C+, non-negative trend, weekly RSI <75." },
      { key: "promote", text: "Runner-up crossing leader threshold. Composite \u226575 with 30-day trend \u2265+8. Manual promotion decision required." },
      { key: "hold", text: "Active position. No add/trim signal. The default state \u2014 patience by design." },
      { key: "await", text: "Runner-up building signal. Analytical hold only, no activation yet." },
      { key: "observe", text: "Observation tier. Scanning, not deciding. No position." },
      { key: "stand-aside", text: "Distribution risk or sharp negative trend. Do not engage regardless of price." }
    ];
    return /* @__PURE__ */ React.createElement("details", { style: { maxWidth: "1400px", margin: `0 auto ${SPACE.xl}px`, fontSize: TYPE.small, color: PALETTE.textSecondary } }, /* @__PURE__ */ React.createElement("summary", { style: { cursor: "pointer", fontFamily: "ui-monospace, monospace", fontSize: TYPE.small, letterSpacing: "0.08em", textTransform: "uppercase", color: PALETTE.textMuted, display: "flex", alignItems: "center", gap: `${SPACE.sm}px`, listStyle: "none", minHeight: isMobile ? "44px" : "auto", padding: isMobile ? `${SPACE.sm}px 0` : 0 } }, /* @__PURE__ */ React.createElement("span", { style: { transition: "transform 0.2s", display: "inline-block" } }, "\u25B8"), "Action rules"), /* @__PURE__ */ React.createElement("style", null, `details[open] summary span:first-child { transform: rotate(90deg); }`), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(280px, 1fr))", gap: `${SPACE.base}px`, marginTop: `${SPACE.lg}px` } }, items.map((item) => {
      const cfg = ACTION_CONFIG[item.key];
      return /* @__PURE__ */ React.createElement("div", { key: item.key, style: { display: "flex", gap: `${SPACE.md}px`, alignItems: "flex-start" } }, /* @__PURE__ */ React.createElement("div", { style: { width: `${SPACE.sm}px`, height: `${SPACE.sm}px`, borderRadius: "50%", background: cfg.dot === "#121110" ? cfg.bg : cfg.dot, marginTop: "5px", flexShrink: 0 } }), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "ui-monospace, monospace", fontSize: TYPE.caption, letterSpacing: "0.08em", textTransform: "uppercase", color: PALETTE.textPrimary, marginBottom: `${SPACE.xs}px`, fontWeight: 500 } }, cfg.label), /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "Georgia, serif", fontStyle: "italic", lineHeight: TYPE.normal } }, item.text)));
    })));
  }
  function LoadingState() {
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "50vh", gap: "16px" } }, /* @__PURE__ */ React.createElement(Loader2, { size: 32, color: PALETTE.textMuted, style: { animation: "spin 1s linear infinite" } }), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.small, color: PALETTE.textMuted, fontFamily: "ui-monospace, monospace" } }, "Loading scores..."), /* @__PURE__ */ React.createElement("style", null, `@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`));
  }
  function ErrorState({ error, onRetry }) {
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "50vh", gap: "16px", padding: "24px" } }, /* @__PURE__ */ React.createElement(AlertCircle, { size: 32, color: "#c27878" }), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.body, color: PALETTE.textPrimary, fontFamily: "Georgia, serif", textAlign: "center" } }, "Failed to load scoring data"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.small, color: PALETTE.textMuted, fontFamily: "ui-monospace, monospace", textAlign: "center", maxWidth: "400px" } }, error), /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: onRetry,
        style: {
          background: "transparent",
          color: PALETTE.textPrimary,
          border: `1px solid ${PALETTE.borderStrong}`,
          padding: "8px 16px",
          fontSize: TYPE.small,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          fontFamily: "ui-monospace, monospace",
          cursor: "pointer",
          marginTop: "8px"
        }
      },
      "Retry"
    ));
  }
  function Dashboard() {
    const [assets, setAssets] = useState([]);
    const [generatedAt, setGeneratedAt] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTier, setActiveTier] = useState("all");
    const isMobile = useIsMobile();
    const fetchData = () => {
      setLoading(true);
      setError(null);
      fetch(`./latest.json?t=${Date.now()}`, { cache: "no-store" }).then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      }).then((data) => {
        setAssets(data.assets || []);
        setGeneratedAt(data.generated_at);
        setLoading(false);
      }).catch((err) => {
        setError(err.message);
        setLoading(false);
      });
    };
    useEffect(() => {
      fetchData();
    }, []);
    const filteredAssets = useMemo(() => {
      const sorted = [...assets].sort((a, b) => {
        const aStrong = a.action === "strong-accumulate" ? 0 : 1;
        const bStrong = b.action === "strong-accumulate" ? 0 : 1;
        const tierDiff = (TIER_CONFIG[a.tier]?.order || 0) - (TIER_CONFIG[b.tier]?.order || 0);
        if (tierDiff !== 0) return tierDiff;
        if (aStrong !== bStrong) return aStrong - bStrong;
        return (b.composite || 0) - (a.composite || 0);
      });
      if (activeTier === "all") return sorted;
      return sorted.filter((a) => a.tier === activeTier);
    }, [activeTier, assets]);
    const groupedAssets = useMemo(() => {
      const groups = { leader: [], "runner-up": [], observation: [] };
      filteredAssets.forEach((a) => {
        if (groups[a.tier]) {
          groups[a.tier].push(a);
        } else {
          console.warn(`Unknown tier "${a.tier}" for asset ${a.symbol}, skipping`);
        }
      });
      return groups;
    }, [filteredAssets]);
    const strongCount = assets.filter((a) => a.action === "strong-accumulate").length;
    if (loading) {
      return /* @__PURE__ */ React.createElement("div", { style: { minHeight: "100vh", background: PALETTE.bg, fontFamily: "Georgia, serif", color: PALETTE.textPrimary } }, /* @__PURE__ */ React.createElement(LoadingState, null));
    }
    if (error) {
      return /* @__PURE__ */ React.createElement("div", { style: { minHeight: "100vh", background: PALETTE.bg, fontFamily: "Georgia, serif", color: PALETTE.textPrimary } }, /* @__PURE__ */ React.createElement(ErrorState, { error, onRetry: fetchData }));
    }
    return /* @__PURE__ */ React.createElement("div", { style: {
      minHeight: "100vh",
      background: PALETTE.bg,
      fontFamily: "Georgia, serif",
      color: PALETTE.textPrimary,
      padding: isMobile ? `${SPACE.lg}px ${SPACE.base}px` : `${SPACE["2xl"]}px ${SPACE.lg}px`
    } }, /* @__PURE__ */ React.createElement("div", { style: { maxWidth: "1400px", margin: `0 auto ${isMobile ? SPACE.lg : SPACE["2xl"]}px`, borderBottom: `1px solid ${PALETTE.borderStrong}`, paddingBottom: `${SPACE.lg}px` } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: isMobile ? "column" : "row", justifyContent: "space-between", alignItems: isMobile ? "stretch" : "flex-start", gap: `${SPACE.lg}px` } }, /* @__PURE__ */ React.createElement("div", { style: { flex: "1 1 auto" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.caption, letterSpacing: "0.15em", textTransform: "uppercase", color: PALETTE.textMuted, marginBottom: `${SPACE.sm}px`, fontFamily: "ui-monospace, monospace" } }, "Framework \xB7 Daily scan"), /* @__PURE__ */ React.createElement("h1", { style: { fontSize: isMobile ? "1.75rem" : TYPE.title, fontWeight: 400, margin: 0, letterSpacing: "-0.01em", lineHeight: 1.1, color: PALETTE.textPrimary } }, "Conviction Scores"), /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.body, color: PALETTE.textSecondary, marginTop: `${SPACE.sm}px`, fontStyle: "italic" } }, "5 dimensions \xB7 Tiered weights by asset type \xB7 RSI confirmation layer"), generatedAt && /* @__PURE__ */ React.createElement("div", { style: { fontSize: TYPE.small, color: isStale(generatedAt) ? "#d49a6a" : PALETTE.textMuted, marginTop: `${SPACE.sm}px`, fontFamily: "ui-monospace, monospace", display: "flex", alignItems: "center", gap: `${SPACE.sm}px` } }, isStale(generatedAt) && /* @__PURE__ */ React.createElement(AlertCircle, { size: 12, color: "#d49a6a", strokeWidth: 2 }), /* @__PURE__ */ React.createElement("span", null, "Updated ", relativeTime(generatedAt), isStale(generatedAt) ? " \xB7 Data may be stale" : ""))), strongCount > 0 && /* @__PURE__ */ React.createElement("div", { style: { padding: `${SPACE.md}px ${SPACE.base}px`, background: "#0f2028", border: "1px solid #4ac0e0", display: "inline-flex", alignItems: "center", gap: `${SPACE.sm}px`, flexShrink: 0 } }, /* @__PURE__ */ React.createElement(Zap, { size: 14, color: "#4ac0e0", fill: "#4ac0e0", strokeWidth: 1.75 }), /* @__PURE__ */ React.createElement("span", { style: { fontSize: TYPE.caption, letterSpacing: "0.1em", textTransform: "uppercase", color: "#4ac0e0", fontFamily: "ui-monospace, monospace", fontWeight: 600 } }, strongCount, " Strong Accumulate signal", strongCount > 1 ? "s" : "", " active")))), /* @__PURE__ */ React.createElement(ActionLegend, { isMobile }), /* @__PURE__ */ React.createElement("div", { style: { maxWidth: "1400px", margin: `0 auto ${SPACE.xl}px`, display: "flex", gap: `${SPACE.sm}px`, flexWrap: "wrap" } }, [
      { id: "all", label: "All" },
      { id: "leader", label: "Leaders" },
      { id: "runner-up", label: "Runner-ups" },
      { id: "observation", label: "Observation" }
    ].map((t) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: t.id,
        onClick: () => setActiveTier(t.id),
        style: {
          background: activeTier === t.id ? PALETTE.textPrimary : "transparent",
          color: activeTier === t.id ? PALETTE.bg : PALETTE.textPrimary,
          border: `1px solid ${PALETTE.borderStrong}`,
          padding: isMobile ? `${SPACE.md}px ${SPACE.base}px` : `${SPACE.sm}px ${SPACE.base}px`,
          minHeight: isMobile ? "44px" : "auto",
          fontSize: TYPE.small,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          fontFamily: "ui-monospace, monospace",
          cursor: "pointer"
        }
      },
      t.label
    ))), /* @__PURE__ */ React.createElement("div", { style: { maxWidth: "1400px", margin: "0 auto" } }, ["leader", "runner-up", "observation"].map((tier) => {
      const config = TIER_CONFIG[tier];
      const tierAssets = groupedAssets[tier];
      if (tierAssets.length === 0 && activeTier !== tier) return null;
      return /* @__PURE__ */ React.createElement("div", { key: tier, style: { marginBottom: `${SPACE["3xl"]}px` } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: `${SPACE.md}px`, marginBottom: `${SPACE.lg}px` } }, /* @__PURE__ */ React.createElement("div", { style: { width: `${SPACE.xl}px`, height: "1px", background: config.accent } }), /* @__PURE__ */ React.createElement("h2", { style: { fontSize: TYPE.small, letterSpacing: "0.15em", textTransform: "uppercase", color: config.accent, fontFamily: "ui-monospace, monospace", fontWeight: 500, margin: 0 } }, config.label, " \u2014 ", tierAssets.length)), tierAssets.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: {
        textAlign: "center",
        padding: `${SPACE["2xl"]}px ${SPACE.lg}px`,
        color: PALETTE.textMuted,
        fontFamily: "Georgia, serif",
        fontStyle: "italic",
        fontSize: TYPE.body,
        background: PALETTE.cardBg,
        border: `1px dashed ${PALETTE.border}`
      } }, "No assets in this tier yet") : /* @__PURE__ */ React.createElement("div", { style: {
        display: "grid",
        gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fill, minmax(300px, 1fr))",
        gap: `${isMobile ? SPACE.base : SPACE.lg}px`
      } }, tierAssets.map((asset) => /* @__PURE__ */ React.createElement(ScoreCard, { key: asset.symbol, asset, isMobile }))));
    })), /* @__PURE__ */ React.createElement("div", { style: { maxWidth: "1400px", margin: `${isMobile ? SPACE["2xl"] : SPACE["3xl"]}px auto 0`, borderTop: `1px solid ${PALETTE.border}`, paddingTop: `${SPACE.lg}px` } }, /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(240px, 1fr))", gap: `${SPACE.lg}px`, fontSize: TYPE.small, color: PALETTE.textMuted, fontFamily: "ui-monospace, monospace", letterSpacing: "0.03em", lineHeight: TYPE.relaxed } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { color: PALETTE.textSecondary, marginBottom: `${SPACE.xs}px`, fontWeight: 500 } }, "Scoring"), "Daily conviction framework. Data refreshed at 12:00 UTC."), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { color: PALETTE.textSecondary, marginBottom: `${SPACE.xs}px`, fontWeight: 500 } }, "Dimensions"), "Institutional \xB7 Revenue \xB7 Regulatory \xB7 Supply \xB7 Wyckoff"), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { color: PALETTE.textSecondary, marginBottom: `${SPACE.xs}px`, fontWeight: 500 } }, "Strong Accumulate"), "Fires when leader sees daily RSI flush with weekly + composite intact."))));
  }
  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(/* @__PURE__ */ React.createElement(Dashboard, null));
})();
