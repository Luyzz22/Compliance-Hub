"use client";

import React, { useEffect, useRef, useState } from "react";

const slides = [
  {
    id: "control-plane",
    label: "Control Plane",
    title: "Vom AI-Inventar zum kontrollierten System.",
    description:
      "Systeme, Pflichten, Controls und Verantwortliche werden als prüfbarer Governance-Kontext verbunden.",
    image: "/images/hero/governance-control-plane.webp",
    imageWidth: 1568,
    imageHeight: 1003,
    imageAlt:
      "Abstrakte Governance-Architektur mit einem dunklen Kontrollkern, verbundenen Kontrollpunkten und transparenten Policy-Ebenen",
  },
  {
    id: "evidence-chain",
    label: "Evidence Chain",
    title: "Herkunft und Review bleiben sichtbar.",
    description:
      "Anforderungen behalten Quelle, Owner, Status und Review-Kontext bis zum strukturierten Nachweis.",
    image: "/images/hero/evidence-chain.webp",
    imageWidth: 1587,
    imageHeight: 991,
    imageAlt:
      "Abstrakte Nachweiskette aus transparenten Ebenen, verbunden mit einem geordneten Evidenzarchiv",
  },
  {
    id: "executive-readiness",
    label: "Board Readiness",
    title: "Offene Punkte werden entscheidbar.",
    description:
      "Risiken, Abhängigkeiten und Maßnahmen werden verdichtet. Die verbindliche Entscheidung bleibt beim Menschen.",
    image: "/images/hero/executive-readiness.webp",
    imageWidth: 1568,
    imageHeight: 1003,
    imageAlt:
      "Abstrakte Executive-Landschaft aus konzentrischen Ringen, Kontrollpunkten und einem nachvollziehbaren Entscheidungspfad",
  },
] as const;

function previousIndex(index: number): number {
  return (index - 1 + slides.length) % slides.length;
}

function nextIndex(index: number): number {
  return (index + 1) % slides.length;
}

export function HomeHeroSlides() {
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(true);
  const rootRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    if (!playing || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    const timer = window.setInterval(() => {
      if (
        document.hidden ||
        rootRef.current?.matches(":hover") ||
        rootRef.current?.contains(document.activeElement)
      ) {
        return;
      }
      setActive((current) => nextIndex(current));
    }, 9_000);

    return () => window.clearInterval(timer);
  }, [playing]);

  function selectSlide(index: number, focus = false) {
    setActive(index);
    if (focus) tabRefs.current[index]?.focus();
  }

  function handleTabKeyDown(
    event: React.KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      selectSlide(previousIndex(index), true);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      selectSlide(nextIndex(index), true);
    } else if (event.key === "Home") {
      event.preventDefault();
      selectSlide(0, true);
    } else if (event.key === "End") {
      event.preventDefault();
      selectSlide(slides.length - 1, true);
    }
  }

  return (
    <div
      ref={rootRef}
      className="min-w-0"
      role="region"
      aria-roledescription="Karussell"
      aria-label="Drei Perspektiven auf Compliance Hub"
    >
      <div className="relative min-h-[34rem] overflow-hidden rounded-2xl border border-[var(--ch-border-strong)] bg-white shadow-[0_34px_90px_rgba(31,35,40,0.12)] sm:min-h-[39rem] lg:min-h-[38rem]">
        {slides.map((slide, index) => {
          const isActive = index === active;

          return (
            <article
              key={slide.id}
              id={`hero-panel-${slide.id}`}
              role="tabpanel"
              aria-labelledby={`hero-tab-${slide.id}`}
              aria-hidden={!isActive}
              inert={!isActive}
              className={`absolute inset-0 grid grid-rows-[64%_36%] transition-[opacity,transform] duration-500 ease-out sm:grid-rows-[70%_30%] ${
                isActive
                  ? "z-10 translate-y-0 opacity-100"
                  : "z-0 translate-y-2 opacity-0"
              }`}
            >
              <div className="overflow-hidden bg-[var(--ch-surface-subtle)]">
                {/* Next/Image currently emits an inline presentation attribute blocked by the strict nonce CSP. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={slide.image}
                  alt={slide.imageAlt}
                  width={slide.imageWidth}
                  height={slide.imageHeight}
                  loading={index === 0 ? "eager" : "lazy"}
                  fetchPriority={index === 0 ? "high" : "auto"}
                  decoding="async"
                  className={`h-full w-full object-cover transition-transform duration-700 ease-out ${
                    isActive ? "scale-100" : "scale-[1.015]"
                  }`}
                />
              </div>
              <div className="grid content-center border-t border-[var(--ch-border)] px-5 py-5 sm:px-7">
                <h2 className="text-xl font-semibold leading-tight tracking-[-0.025em] text-[var(--ch-ink)] sm:text-2xl">
                  {slide.title}
                </h2>
                <p className="mt-2 max-w-[58ch] text-sm leading-6 text-[var(--ch-muted)]">
                  {slide.description}
                </p>
              </div>
            </article>
          );
        })}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-center">
        <div
          className="grid grid-cols-3 border border-[var(--ch-border)] bg-white"
          role="tablist"
          aria-label="Hero-Slides"
        >
          {slides.map((slide, index) => (
            <button
              key={slide.id}
              ref={(element) => {
                tabRefs.current[index] = element;
              }}
              id={`hero-tab-${slide.id}`}
              type="button"
              role="tab"
              aria-controls={`hero-panel-${slide.id}`}
              aria-selected={index === active}
              tabIndex={index === active ? 0 : -1}
              onClick={() => selectSlide(index)}
              onKeyDown={(event) => handleTabKeyDown(event, index)}
              className={`min-h-12 border-r border-[var(--ch-border)] px-2 text-left text-[0.68rem] font-semibold transition-colors last:border-r-0 sm:px-4 sm:text-xs ${
                index === active
                  ? "bg-[var(--ch-accent)] text-white"
                  : "bg-white text-[var(--ch-muted)] hover:bg-[var(--ch-surface-subtle)] hover:text-[var(--ch-ink)]"
              }`}
            >
              <span className="block truncate">{slide.label}</span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Vorherige Slide"
            onClick={() => selectSlide(previousIndex(active))}
            className="home-control-button"
          >
            Zurück
          </button>
          <button
            type="button"
            aria-label={
              playing
                ? "Automatischen Wechsel pausieren"
                : "Automatischen Wechsel starten"
            }
            aria-pressed={!playing}
            onClick={() => setPlaying((current) => !current)}
            className="home-control-button"
          >
            {playing ? "Pausieren" : "Abspielen"}
          </button>
          <button
            type="button"
            aria-label="Nächste Slide"
            onClick={() => selectSlide(nextIndex(active))}
            className="home-control-button"
          >
            Weiter
          </button>
        </div>
      </div>
    </div>
  );
}
