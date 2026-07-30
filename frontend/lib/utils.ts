import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { randomUUID } from "crypto"

export function generateId(): string {
  return randomUUID()
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Humanize a raw Google Places category slug (e.g. "sports_club" -> "Sports club"). */
export function formatCategory(category?: string | null): string | undefined {
  if (!category) return undefined
  const spaced = category.replace(/_/g, " ").trim()
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : undefined
}
