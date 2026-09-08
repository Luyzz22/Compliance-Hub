"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useCallback, useEffect, useRef, useState } from "react";

import {
  MARKETING_NAV,
  MARKETING_ROUTES,
  type MarketingNavGroup,
} from "@/lib/marketing/navigation";

import { IconChevronDown, IconClose, IconMenu } from "./ui/Icons";

/**
 * Die Hausmarke.
 *
 * Konstruktion und Bauteile sind dieselben wie beim Schwesterprodukt
 * NormPilot Industrie: Schild in Petrol-Navy, drei Registerlinien absteigender
 * Länge, ein Messingsiegel unten rechts. Das Siegel trägt hier ein Häkchen
 * statt einer Lupe — NormPilot prüft, Compliance Hub belegt. Gleiche Familie,
 * andere Handlung; genau daran soll die Verwandtschaft erkennbar sein.
 *
 * Die Verläufe brauchen dokumentweit eindeutige `id`-Werte: erscheint dieselbe
 * `id` ein zweites Mal im DOM, greifen alle Referenzen auf die erste Definition
 * zu.
 */
function BrandMark() {
  return (
    <Link
      href={MARKETING_ROUTES.home}
      prefetch={false}
      className="flex shrink-0 items-center gap-2.5 no-underline"
    >
      <svg
        viewBox="0 0 32 32"
        className="h-8 w-8 shrink-0"
        aria-hidden
        focusable="false"
      >
        <defs>
          <linearGradient id="ch-mark-navy" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0e4d6e" />
            <stop offset="100%" stopColor="#003856" />
          </linearGradient>
          <linearGradient id="ch-mark-brass" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#d2b26f" />
            <stop offset="100%" stopColor="#b98f42" />
          </linearGradient>
        </defs>
        <path
          d="M16 2L5 7v10c0 7.2 4.7 12.1 11 13 6.3-.9 11-5.8 11-13V7L16 2z"
          fill="url(#ch-mark-navy)"
        />
        <path
          d="M16 4.5L7 8.5v8.5c0 5.8 3.8 9.8 9 10.5 5.2-.7 9-4.7 9-10.5V8.5L16 4.5z"
          fill="none"
          stroke="#ffffff"
          strokeWidth="0.5"
          opacity="0.15"
        />
        <line x1="11" y1="11" x2="21" y2="11" stroke="#ffffff" strokeWidth="1.2" strokeLinecap="round" opacity="0.7" />
        <line x1="11" y1="14.5" x2="19" y2="14.5" stroke="#ffffff" strokeWidth="1.2" strokeLinecap="round" opacity="0.5" />
        <line x1="11" y1="18" x2="17" y2="18" stroke="#ffffff" strokeWidth="1.2" strokeLinecap="round" opacity="0.35" />
        <circle cx="21" cy="19" r="3.1" fill="url(#ch-mark-brass)" />
        <path
          d="M19.6 19.1l1 1.05 1.9-2.1"
          fill="none"
          stroke="#0c1216"
          strokeWidth="1.1"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="leading-tight">
        <span className="block whitespace-nowrap text-[0.9375rem] font-semibold tracking-[-0.02em] text-white">
          Compliance Hub
        </span>
        <span className="hidden whitespace-nowrap text-[0.625rem] font-medium text-[var(--mk-fg-faint)] 2xl:block">
          Governance für AI, Security &amp; Compliance
        </span>
      </span>
    </Link>
  );
}

function DesktopGroup({
  group,
  isActive,
}: {
  group: MarketingNavGroup;
  isActive: (href: string) => boolean;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelClose = useCallback(() => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  }, []);

  const scheduleClose = useCallback(() => {
    cancelClose();
    closeTimer.current = setTimeout(() => setOpen(false), 120);
  }, [cancelClose]);

  useEffect(() => cancelClose, [cancelClose]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    function onPointerDown(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, [open]);

  if (!group.items) {
    return (
      <Link
        href={group.href ?? "#"}
        prefetch={false}
        className="mk-navlink"
        data-active={isActive(group.href ?? "") ? "true" : "false"}
      >
        {group.label}
      </Link>
    );
  }

  const groupActive = group.items.some((item) => {
    const [path, hash] = item.href.split("#");
    if (hash && path !== group.href) return false;
    return isActive(path);
  });

  return (
    <div
      ref={containerRef}
      className="relative"
      onMouseEnter={() => {
        cancelClose();
        setOpen(true);
      }}
      onMouseLeave={scheduleClose}
      onFocus={cancelClose}
      onBlur={(event) => {
        if (!containerRef.current?.contains(event.relatedTarget as Node)) {
          setOpen(false);
        }
      }}
    >
      <button
        type="button"
        className="mk-navlink"
        aria-expanded={open}
        aria-haspopup="true"
        data-active={groupActive ? "true" : "false"}
        onClick={() => setOpen((current) => !current)}
      >
        {group.label}
        <IconChevronDown className="h-3 w-3 opacity-60" />
      </button>
      {open ? (
        <div className="mk-menu" role="menu" aria-label={group.label}>
          {group.items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              prefetch={false}
              role="menuitem"
              className="mk-menu-item"
              onClick={() => setOpen(false)}
            >
              <span className="block text-[0.8125rem] font-semibold text-white">
                {item.label}
              </span>
              {item.description ? (
                <span className="mt-0.5 block text-[0.6875rem] leading-relaxed text-[var(--mk-fg-faint)]">
                  {item.description}
                </span>
              ) : null}
            </Link>
          ))}
          {group.footnote ? (
            <p className="mt-1 border-t border-[var(--mk-bd)] px-3 pb-1 pt-2.5 text-[0.625rem] leading-relaxed text-[var(--mk-fg-faint)]">
              {group.footnote}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function MobileNav({
  onClose,
  isActive,
  showLogin,
}: {
  onClose: () => void;
  isActive: (href: string) => boolean;
  showLogin: boolean;
}) {
  return (
    <div
      id="marketing-mobile-nav"
      className="mk-stage max-h-[calc(100dvh-4rem)] overflow-y-auto border-t border-[var(--mk-bd)] xl:hidden"
    >
      <nav aria-label="Hauptnavigation mobil" className="mk-container py-4">
        <ul className="divide-y divide-[var(--mk-bd)]">
          {MARKETING_NAV.map((group) => (
            <li key={group.id} className="py-2.5">
              {group.href ? (
                <Link
                  href={group.href}
                  prefetch={false}
                  onClick={onClose}
                  className="block py-2 text-[0.9375rem] font-semibold text-white no-underline"
                  data-active={isActive(group.href) ? "true" : "false"}
                >
                  {group.label}
                </Link>
              ) : (
                <p className="py-2 text-[0.6875rem] font-bold uppercase tracking-[0.12em] text-[var(--mk-fg-faint)]">
                  {group.label}
                </p>
              )}
              {group.items ? (
                <ul className="space-y-0.5 pb-1">
                  {group.items
                    .filter((item) => item.href !== group.href)
                    .map((item) => (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          prefetch={false}
                          onClick={onClose}
                          className="block rounded-[6px] py-2 text-[0.8125rem] text-[var(--mk-fg-muted)] no-underline"
                        >
                          {item.label}
                        </Link>
                      </li>
                    ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>

        <div className="mt-4 flex flex-col gap-2">
          <Link
            href={MARKETING_ROUTES.demo}
            prefetch={false}
            onClick={onClose}
            className="mk-btn mk-btn--primary"
          >
            Demo anfragen
          </Link>
          <Link
            href={MARKETING_ROUTES.productTour}
            prefetch={false}
            onClick={onClose}
            className="mk-btn mk-btn--secondary"
          >
            5-Minuten Produkt-Tour
          </Link>
          {showLogin ? (
            <Link
              href="/auth/login"
              prefetch={false}
              onClick={onClose}
              className="mk-btn mk-btn--ghost"
            >
              Login
            </Link>
          ) : null}
        </div>
      </nav>
    </div>
  );
}

/**
 * Sticky Hauptnavigation der Website.
 * `showLogin` ist an das Release-Profil gebunden: Im rein öffentlichen Release
 * existiert keine Anmeldung, dann wird der Login-Einstieg nicht angeboten.
 */
export function MarketingHeader({ showLogin = false }: { showLogin?: boolean }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 8);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const isActive = useCallback(
    (href: string) => {
      if (!href) return false;
      if (href === "/") return pathname === "/";
      return pathname === href || pathname.startsWith(`${href}/`);
    },
    [pathname],
  );

  return (
    <header
      className="mk-stage mk-stage-veil mk-header"
      data-scrolled={scrolled ? "true" : "false"}
    >
      <div className="mk-container flex min-h-16 items-center justify-between gap-4">
        <BrandMark />

        <nav aria-label="Hauptnavigation" className="hidden items-center gap-0.5 xl:flex">
          {MARKETING_NAV.map((group) => (
            <DesktopGroup key={group.id} group={group} isActive={isActive} />
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {showLogin ? (
            <Link href="/auth/login" prefetch={false} className="mk-navlink hidden xl:inline-flex">
              Login
            </Link>
          ) : null}
          <Link
            href={MARKETING_ROUTES.productTour}
            prefetch={false}
            className="mk-btn mk-btn--secondary mk-btn--sm hidden 2xl:inline-flex"
          >
            Produkt-Tour
          </Link>
          <Link
            href={MARKETING_ROUTES.demo}
            prefetch={false}
            className="mk-btn mk-btn--primary mk-btn--sm"
          >
            Demo anfragen
          </Link>
          <button
            type="button"
            className="mk-btn mk-btn--ghost mk-btn--sm xl:hidden"
            aria-label={mobileOpen ? "Menü schließen" : "Menü öffnen"}
            aria-expanded={mobileOpen}
            aria-controls="marketing-mobile-nav"
            onClick={() => setMobileOpen((current) => !current)}
          >
            {mobileOpen ? (
              <IconClose className="h-5 w-5" />
            ) : (
              <IconMenu className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {mobileOpen ? (
        <MobileNav
          onClose={() => setMobileOpen(false)}
          isActive={isActive}
          showLogin={showLogin}
        />
      ) : null}
    </header>
  );
}
