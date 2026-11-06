import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number | undefined | null): string {
  if (amount === undefined || amount === null || isNaN(amount)) return "$0";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return "N/A";
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

export function cleanSignalText(content: string | undefined | null): string {
  if (!content) return "";
  let text = content;
  // Replace block endings and break tags with spaces
  text = text.replace(/<\/(p|div|li)>/gi, " ");
  text = text.replace(/<(br|hr)\s*\/?>/gi, " ");
  // Strip all HTML tags
  text = text.replace(/<[^>]+>/g, "");
  // Decode common HTML entities
  text = text
    .replace(/&quot;/gi, '"')
    .replace(/&#x27;|&#39;|&apos;/gi, "'")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&nbsp;/gi, " ");
  // Normalize extra whitespace
  return text.replace(/\s+/g, " ").trim();
}

import type { DecisionMaker } from "@/types";

export function formatDecisionMaker(dm: DecisionMaker | null | undefined): string | null {
  if (dm === null || dm === undefined) return null;

  if (typeof dm === "string") {
    const trimmed = dm.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (typeof dm === "object") {
    const role = typeof dm.role === "string" ? dm.role.trim() : typeof dm.title === "string" ? dm.title.trim() : "";
    const dept = typeof dm.department === "string" ? dm.department.trim() : "";
    const name = typeof dm.name === "string" ? dm.name.trim() : "";

    if (name) {
      if (role && dept) return `${name} (${role} · ${dept})`;
      if (role) return `${name} (${role})`;
      if (dept) return `${name} (${dept})`;
      return name;
    }

    if (role && dept) return `${role} · ${dept}`;
    if (role) return role;
    if (dept) return dept;

    for (const val of Object.values(dm)) {
      if (typeof val === "string" && val.trim().length > 0 && val.trim() !== "[object Object]") {
        return val.trim();
      }
    }
    return null;
  }

  const str = String(dm).trim();
  return str.length > 0 && str !== "[object Object]" ? str : null;
}
