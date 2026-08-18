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

function BrandMark() {
  return (
    <Link
      href={MARKETING_ROUTES.home}
      prefetch={false}
      className="flex min-w-0 items-center gap-2.5 no-underline"
    >
      <span
        aria-hidden
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] bg-[var(--mk-navy-900)] text-white"
      >
        <svg viewBox="0 0 24 24" className="h-4.5 w-4.5" fill="none" aria-hidden>
          <path
            d="M12 3.5 19 6.2v5.6c0 3.8-2.8 6.9-7 8.2-4.2-1.3-7-4.4-7-8.2V6.2z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <path
            d="M9 12.1 11 14.2l4-4.3"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span className="min-w-0 leading-tight">
        <span className="block truncate text-[0.9375rem] font-semibold tracking-[-0.02em] text-[var(--mk-navy-900)]">
          Compliance Hub
        </span>
        <span className="hidden text-[0.625rem] font-medium text-[var(--mk-slate-500)] sm:block">
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

  const groupActive = group.items.some((item) => isActive(item.href.split("#")[0]));

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
              <span className="block text-[0.8125rem] font-semibold text-[var(--mk-navy-900)]">
                {item.label}
              </span>
              {item.description ? (
                <span className="mt-0.5 block text-[0.6875rem] leading-relaxed text-[var(--mk-slate-500)]">
                  {item.description}
                </span>
              ) : null}
            </Link>
          ))}
          {group.footnote ? (
            <p className="mt-1 border-t border-[var(--mk-slate-200)] px-3 pb-1 pt-2.5 text-[0.625rem] leading-relaxed text-[var(--mk-slate-400)]">
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
      className="max-h-[calc(100dvh-4rem)] overflow-y-auto border-t border-[var(--mk-slate-200)] bg-white lg:hidden"
    >
      <nav aria-label="Hauptnavigation mobil" className="mk-container py-4">
        <ul className="divide-y divide-[var(--mk-slate-200)]">
          {MARKETING_NAV.map((group) => (
            <li key={group.id} className="py-2.5">
              {group.href ? (
                <Link
                  href={group.href}
                  prefetch={false}
                  onClick={onClose}
                  className="block py-2 text-[0.9375rem] font-semibold text-[var(--mk-navy-900)] no-underline"
                  data-active={isActive(group.href) ? "true" : "false"}
                >
                  {group.label}
                </Link>
              ) : (
                <p className="py-2 text-[0.6875rem] font-bold uppercase tracking-[0.12em] text-[var(--mk-slate-400)]">
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
                          className="block rounded-[6px] py-2 text-[0.8125rem] text-[var(--mk-slate-600)] no-underline"
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
    <header className="mk-header" data-scrolled={scrolled ? "true" : "false"}>
      <div className="mk-container flex min-h-16 items-center justify-between gap-4">
        <BrandMark />

        <nav aria-label="Hauptnavigation" className="hidden items-center gap-0.5 lg:flex">
          {MARKETING_NAV.map((group) => (
            <DesktopGroup key={group.id} group={group} isActive={isActive} />
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {showLogin ? (
            <Link href="/auth/login" prefetch={false} className="mk-navlink hidden sm:inline-flex">
              Login
            </Link>
          ) : null}
          <Link
            href={MARKETING_ROUTES.productTour}
            prefetch={false}
            className="mk-btn mk-btn--secondary mk-btn--sm hidden xl:inline-flex"
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
            className="mk-btn mk-btn--ghost mk-btn--sm lg:hidden"
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
