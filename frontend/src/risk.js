// Risk/status → presentation for the paper-studio (light) theme.
// Risk is the primary signal (color), confidence is always shown as a number,
// and escalation ("needs human review") is a distinct treatment, not a hint.

export const RISK = {
  HIGH: {
    label: "High",
    dot: "bg-red-500",
    text: "text-red-600",
    border: "border-l-red-500",
    badge: "border-red-500/40 bg-red-500/[0.06] text-red-700",
    strip: "bg-red-500/10",
  },
  MEDIUM: {
    label: "Medium",
    dot: "bg-amber-500",
    text: "text-amber-700",
    border: "border-l-amber-500",
    badge: "border-amber-500/40 bg-amber-500/[0.08] text-amber-800",
    strip: "bg-amber-500/10",
  },
  LOW: {
    label: "Low",
    dot: "bg-yellow-500",
    text: "text-yellow-700",
    border: "border-l-yellow-500",
    badge: "border-yellow-600/40 bg-yellow-500/[0.08] text-yellow-800",
    strip: "bg-yellow-500/10",
  },
  NONE: {
    label: "None",
    dot: "bg-stone-400",
    text: "text-stone-500",
    border: "border-l-stone-400",
    badge: "border-stone-400/40 bg-stone-400/15 text-stone-700",
    strip: "bg-stone-400/10",
  },
};

export const STATUS = {
  DEVIATION: { label: "Deviation", badge: "bg-red-500/[0.07] text-red-700" },
  COMPLIANT: { label: "Compliant", badge: "bg-emerald-500/10 text-emerald-700" },
};

export function riskConfig(level) {
  return RISK[level] || RISK.NONE;
}

export function statusConfig(status) {
  return STATUS[status] || { label: status, badge: "" };
}
