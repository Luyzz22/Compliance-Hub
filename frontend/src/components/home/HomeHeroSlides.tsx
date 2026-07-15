"use client";

import Link from "next/link";
import React, { useEffect, useRef, useState } from "react";

import { contactPageHref } from "@/lib/publicContact";

const slides = [
  {
    id: "control-plane",
    index: "01",
    label: "Control Plane",
    eyebrow: "Governance architecture",
    title: "Vom AI-Inventar zum kontrollierten System.",
    description:
      "Systeme, Pflichten, Controls und Verantwortliche werden in einer nachvollziehbaren Struktur verbunden – als Grundlage für Review, Freigabe und Betrieb.",
    image: "/images/hero/governance-control-plane.webp",
    imageWidth: 1568,
    imageHeight: 1003,
    imageAlt:
      "Abstrakte Governance-Architektur aus einem dunklen Glaskern, verbundenen Kontrollpunkten und transparenten Policy-Ebenen",
    ctaLabel: "Governance-Architektur besprechen",
    ctaHref: contactPageHref({
      quelle: "hero-control-plane",
      ctaId: "hero-control-plane-briefing",
      ctaLabel: "Governance-Architektur besprechen",
    }),
    proof: [
      { value: "5", label: "Regelwerke im Kontrollmodell" },
      { value: "1", label: "Gemeinsamer Control Graph" },
      { value: "Human", label: "Review bleibt verbindlich" },
    ],
  },
  {
    id: "evidence-chain",
    index: "02",
    label: "Evidence Chain",
    eyebrow: "Auditability by design",
    title: "Evidence, die Herkunft und Review sichtbar macht.",
    description:
      "Anforderungen erhalten Quelle, Owner, Status und Review-Kontext. So entsteht eine belastbare Nachweiskette – ohne eine Prüfung oder Rechtsbewertung zu automatisieren.",
    image: "/images/hero/evidence-chain.webp",
    imageWidth: 1587,
    imageHeight: 991,
    imageAlt:
      "Abstrakte Nachweiskette aus transparenten Ebenen, die durch einen grünen Faden mit einem geordneten Archiv verbunden sind",
    ctaLabel: "Evidence-Review anfragen",
    ctaHref: contactPageHref({
      quelle: "hero-evidence-chain",
      ctaId: "hero-evidence-review",
      ctaLabel: "Evidence-Review anfragen",
    }),
    proof: [
      { value: "Trace", label: "Quelle und Änderungskontext" },
      { value: "Review", label: "Owner und Freigabestatus" },
      { value: "Export", label: "Strukturierte Nachweispfade" },
    ],
  },
  {
    id: "executive-readiness",
    index: "03",
    label: "Board Readiness",
    eyebrow: "Decision intelligence",
    title: "Vom Kontrollstatus zur verantwortbaren Entscheidung.",
    description:
      "Risiken, Abhängigkeiten und offene Maßnahmen werden für das Board verdichtet. Die Plattform liefert Kontext; Entscheidungen bleiben bei den zuständigen Personen.",
    image: "/images/hero/executive-readiness.webp",
    imageWidth: 1568,
    imageHeight: 1003,
    imageAlt:
      "Abstrakte Executive-Landschaft aus konzentrischen Ringen, Kontrollpunkten und einem nachvollziehbaren grünen Entscheidungspfad",
    ctaLabel: "Executive Briefing planen",
    ctaHref: contactPageHref({
      quelle: "hero-board-readiness",
      ctaId: "hero-executive-briefing",
      ctaLabel: "Executive Briefing planen",
    }),
    proof: [
      { value: "Risk", label: "Priorisierte Entscheidungsfelder" },
      { value: "Owner", label: "Klare Verantwortlichkeiten" },
      { value: "Board", label: "Verdichteter Governance-Kontext" },
    ],
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
    }, 8_000);
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
      <div className="relative min-h-[56rem] overflow-hidden rounded-[2.25rem] border border-slate-200/80 bg-white shadow-[0_40px_120px_rgba(7,17,31,0.13)] sm:min-h-[54rem] lg:min-h-[41rem] lg:rounded-[3rem]">
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
              className={`absolute inset-0 grid h-full grid-rows-[42%_58%] transition duration-700 ease-out lg:grid-cols-[0.92fr_1.08fr] lg:grid-rows-1 ${
                isActive
                  ? "z-10 translate-x-0 opacity-100"
                  : "z-0 translate-x-6 opacity-0"
              }`}
            >
              <div className="order-2 flex min-w-0 flex-col justify-center px-6 py-7 sm:px-10 lg:order-1 lg:px-12 xl:px-16">
                <div className="flex items-center gap-3 text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-slate-500 sm:text-xs">
                  <span className="font-mono text-cyan-700">{slide.index}</span>
                  <span className="h-px w-8 bg-slate-300" aria-hidden />
                  {slide.eyebrow}
                </div>
                <h2 className="mt-5 max-w-xl text-3xl font-semibold leading-[1.02] tracking-[-0.05em] text-[#07111f] sm:text-4xl lg:text-[3.2rem]">
                  {slide.title}
                </h2>
                <p className="mt-5 max-w-xl text-sm leading-7 text-slate-600 sm:text-base">
                  {slide.description}
                </p>

                <dl className="mt-7 grid grid-cols-3 gap-2 border-y border-slate-200/80 py-5">
                  {slide.proof.map((item) => (
                    <div key={item.label} className="min-w-0">
                      <dt className="text-[0.62rem] leading-4 text-slate-500 sm:text-xs">
                        {item.label}
                      </dt>
                      <dd className="mt-1 truncate font-mono text-sm font-semibold text-slate-950 sm:text-base">
                        {item.value}
                      </dd>
                    </div>
                  ))}
                </dl>

                <div className="mt-7 flex flex-wrap gap-3">
                  <Link
                    href={slide.ctaHref}
                    className="inline-flex min-h-11 items-center justify-center rounded-full bg-[#07111f] px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-slate-950/15 transition hover:-translate-y-0.5 hover:bg-slate-800 sm:text-sm"
                  >
                    {slide.ctaLabel}
                  </Link>
                  <Link
                    href="/trust-center"
                    className="inline-flex min-h-11 items-center justify-center rounded-full border border-slate-200 bg-white px-5 py-2.5 text-xs font-semibold text-slate-800 transition hover:-translate-y-0.5 hover:border-slate-300 sm:text-sm"
                  >
                    Trust Center
                  </Link>
                </div>
              </div>

              <div className="relative order-1 m-3 overflow-hidden rounded-[1.6rem] border border-white/70 bg-slate-100 lg:order-2 lg:m-4 lg:ml-0 lg:rounded-[2.25rem]">
                {/* Next/Image emits an inline presentation attribute that strict CSP blocks. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={slide.image}
                  alt={slide.imageAlt}
                  width={slide.imageWidth}
                  height={slide.imageHeight}
                  loading={index === 0 ? "eager" : "lazy"}
                  fetchPriority={index === 0 ? "high" : "auto"}
                  decoding="async"
                  className={`h-full w-full object-cover transition duration-1000 ease-out ${
                    isActive ? "scale-100" : "scale-[1.025]"
                  }`}
                />
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#07111f]/20 via-transparent to-white/10" />
                <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between rounded-2xl border border-white/60 bg-white/78 px-4 py-3 text-xs shadow-lg shadow-slate-950/10 backdrop-blur-xl sm:bottom-6 sm:left-6 sm:right-6">
                  <span className="font-semibold text-slate-900">{slide.label}</span>
                  <span className="flex items-center gap-2 text-slate-600">
                    <span className="h-2 w-2 rounded-full bg-emerald-500" aria-hidden />
                    Kontrollierter Scope
                  </span>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      <div className="mt-5 flex flex-col gap-3 rounded-[1.5rem] border border-slate-200/80 bg-white/85 p-2.5 shadow-lg shadow-slate-200/40 backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between">
        <div
          className="grid flex-1 grid-cols-3 gap-1"
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
              className={`min-w-0 rounded-2xl px-2 py-3 text-left transition sm:px-4 ${
                index === active
                  ? "bg-[#07111f] text-white shadow-md"
                  : "text-slate-500 hover:bg-slate-100 hover:text-slate-950"
              }`}
            >
              <span className="block font-mono text-[0.6rem] opacity-65">
                {slide.index}
              </span>
              <span className="mt-1 block truncate text-[0.65rem] font-semibold sm:text-xs">
                {slide.label}
              </span>
            </button>
          ))}
        </div>

        <div className="flex items-center justify-between gap-2 px-1 sm:justify-end">
          <button
            type="button"
            aria-label="Vorherige Slide"
            onClick={() => selectSlide(previousIndex(active))}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            <span aria-hidden>←</span>
          </button>
          <button
            type="button"
            aria-label={playing ? "Automatischen Wechsel pausieren" : "Automatischen Wechsel starten"}
            aria-pressed={!playing}
            onClick={() => setPlaying((current) => !current)}
            className="inline-flex h-10 min-w-24 items-center justify-center rounded-full border border-slate-200 bg-white px-4 text-xs font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            {playing ? "Pausieren" : "Abspielen"}
          </button>
          <button
            type="button"
            aria-label="Nächste Slide"
            onClick={() => selectSlide(nextIndex(active))}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            <span aria-hidden>→</span>
          </button>
        </div>
      </div>
    </div>
  );
}
