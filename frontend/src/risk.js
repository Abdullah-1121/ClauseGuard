// Risk/status → presentation for the audit-grade dark theme.
// Risk is the primary signal (color), confidence is always shown as a number,
// and escalation ("needs human review") is a distinct treatment, not a hint.

export const RISK = {
  HIGH: {
    label: "High",
    dot: "bg-red-500",
    text: "text-red-400",
    border: "border-l-red-500",
    badge: "border-red-500/30 bg-red-500/10 text-red-300",
    strip: "bg-red-500/15",
  },
  MEDIUM: {
    label: "Medium",
    dot: "bg-amber-400",
    text: "text-amber-300",
    border: "border-l-amber-400",
    badge: "border-amber-400/30 bg-amber-400/10 text-amber-200",
    strip: "bg-amber-400/12",
  },
  LOW: {
    label: "Low",
    dot: "bg-yellow-300",
    text: "text-yellow-200",
    border: "border-l-yellow-300",
    badge: "border-yellow-300/25 bg-yellow-300/8 text-yellow-100",
    strip: "bg-yellow-300/8",
  },
  NONE: {
    label: "None",
    dot: "bg-stone-500",
    text: "text-stone-400",
    border: "border-l-stone-600",
    badge: "border-stone-500/25 bg-stone-500/10 text-stone-300",
    strip: "bg-stone-500/8",
  },
};

export const STATUS = {
  DEVIATION: { label: "Deviation", badge: "bg-red-500/15 text-red-300" },
  COMPLIANT: { label: "Compliant", badge: "bg-emerald-500/12 text-emerald-300" },
};

export function riskConfig(level) {
  return RISK[level] || RISK.NONE;
}

export function statusConfig(status) {
  return STATUS[status] || { label: status, badge: "" };
}
