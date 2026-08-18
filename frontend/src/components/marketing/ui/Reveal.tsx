import React from "react";

type RevealProps = {
  children: React.ReactNode;
  /** Staffelung innerhalb einer Gruppe (0–4) — siehe `animation-range` in marketing.css. */
  delay?: 0 | 1 | 2 | 3 | 4;
  as?: "div" | "section" | "li" | "article";
  className?: string;
};

/**
 * Scroll-Reveal zur Orientierung, nicht zur Dekoration.
 *
 * Die Animation läuft vollständig in CSS über eine scroll-getriebene
 * `view()`-Timeline. Damit gibt es kein JavaScript im Kritischen Pfad und —
 * wichtiger — keinen Zustand, in dem Inhalte dauerhaft unsichtbar bleiben:
 * Ohne Unterstützung für scroll-getriebene Animationen oder bei
 * `prefers-reduced-motion` wird der Inhalt einfach ohne Bewegung angezeigt.
 */
export function Reveal({
  children,
  delay = 0,
  as: Tag = "div",
  className = "",
}: RevealProps) {
  return (
    <Tag className={`mk-reveal ${className}`.trim()} data-delay={delay || undefined}>
      {children}
    </Tag>
  );
}
