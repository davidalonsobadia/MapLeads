// Lead status colors (PRD sec.9).
//
// Small, reusable source of truth for how the four lead statuses are colored
// across the app. Each entry ships:
//   - `hex`: raw palette value, for non-CSS contexts (map pins, canvas, charts).
//   - `badgeClass`: Tailwind utility classes for a soft badge/chip.
//   - `dotClass`: Tailwind background class for a small status dot.
// Later screens should import from here instead of re-deriving colors.

export type LeadStatus = "new" | "contacted" | "interested" | "discarded"

export interface LeadStatusStyle {
  /** Human-readable label. */
  label: string
  /** Raw palette hex, for map pins / canvas / anywhere CSS vars are unavailable. */
  hex: string
  /** Tailwind classes for a soft badge/chip. */
  badgeClass: string
  /** Tailwind background class for a small status dot. */
  dotClass: string
}

export const LEAD_STATUS_STYLES: Record<LeadStatus, LeadStatusStyle> = {
  new: {
    label: "New",
    hex: "#1a73e8", // brand blue
    badgeClass: "bg-accent text-accent-foreground",
    dotClass: "bg-primary",
  },
  contacted: {
    label: "Contacted",
    hex: "#fbbc04", // warning / pending amber
    badgeClass: "bg-warning/15 text-warning-foreground",
    dotClass: "bg-warning",
  },
  interested: {
    label: "Interested",
    hex: "#34a853", // success green
    badgeClass: "bg-success/15 text-success",
    dotClass: "bg-success",
  },
  discarded: {
    label: "Discarded",
    hex: "#ea4335", // error red
    badgeClass: "bg-destructive/15 text-destructive",
    dotClass: "bg-destructive",
  },
}

export const LEAD_STATUSES = Object.keys(LEAD_STATUS_STYLES) as LeadStatus[]

/** Style for a status, falling back to `new` for unknown values. */
export function getLeadStatusStyle(status: string): LeadStatusStyle {
  return LEAD_STATUS_STYLES[status as LeadStatus] ?? LEAD_STATUS_STYLES.new
}
