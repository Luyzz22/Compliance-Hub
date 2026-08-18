import React from "react";

/**
 * Einheitlicher Outline-Icon-Satz (24×24, stroke 1.5, runde Enden).
 * Keine Emoji, kein gemischter Ikonografie-Stil.
 */

type IconProps = {
  className?: string;
  title?: string;
};

function Svg({
  className,
  title,
  children,
}: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className ?? "h-5 w-5"}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      focusable="false"
    >
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  );
}

export function IconRegistry(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4H18a2 2 0 0 1 2 2v12.5" />
      <path d="M6.5 4v16H18a2 2 0 0 0 2-2" />
      <path d="M6.5 20A2.5 2.5 0 0 1 4 17.5V6.5" />
      <path d="M9.5 9h7M9.5 12.5h5" />
    </Svg>
  );
}

export function IconClassify(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3.5 20 8v8l-8 4.5L4 16V8z" />
      <path d="M12 12v8.5M12 12 4 8M12 12l8-4" />
    </Svg>
  );
}

export function IconMapping(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="9.5" width="5" height="5" rx="1.2" />
      <rect x="16" y="3.5" width="5" height="5" rx="1.2" />
      <rect x="16" y="15.5" width="5" height="5" rx="1.2" />
      <path d="M8 12h3.5a1.5 1.5 0 0 0 1.5-1.5V7.5A1.5 1.5 0 0 1 14.5 6H16" />
      <path d="M8 12h3.5a1.5 1.5 0 0 1 1.5 1.5v3A1.5 1.5 0 0 0 14.5 18H16" />
    </Svg>
  );
}

export function IconEvidence(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M14 3.5H7.5A1.5 1.5 0 0 0 6 5v14a1.5 1.5 0 0 0 1.5 1.5h9A1.5 1.5 0 0 0 18 19V7.5z" />
      <path d="M14 3.5V7a.5.5 0 0 0 .5.5H18" />
      <path d="m9 14.5 1.8 1.8 3.7-3.8" />
    </Svg>
  );
}

export function IconBoard(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="4.5" width="18" height="13" rx="1.8" />
      <path d="M7.5 14V11M12 14V8.5M16.5 14v-2" />
      <path d="M9 20.5h6" />
    </Svg>
  );
}

export function IconTenants(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="8.5" width="7" height="12" rx="1.2" />
      <rect x="14" y="3.5" width="7" height="17" rx="1.2" />
      <path d="M5.5 12h2M5.5 15.5h2M16.5 7h2M16.5 11h2M16.5 15h2" />
    </Svg>
  );
}

export function IconShield(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3.5 5 6v6c0 4 3 7.2 7 8.5 4-1.3 7-4.5 7-8.5V6z" />
      <path d="m9.2 12.2 2 2 3.6-3.8" />
    </Svg>
  );
}

export function IconServer(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3.5" y="4" width="17" height="6" rx="1.5" />
      <rect x="3.5" y="14" width="17" height="6" rx="1.5" />
      <path d="M7 7h.01M7 17h.01" />
    </Svg>
  );
}

export function IconKey(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="12" r="3.5" />
      <path d="M11.5 12H20M17 12v3M20 12v2.5" />
    </Svg>
  );
}

export function IconFlow(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3" y="4" width="6" height="5" rx="1.2" />
      <rect x="15" y="15" width="6" height="5" rx="1.2" />
      <path d="M6 9v5.5A2.5 2.5 0 0 0 8.5 17H15" />
      <path d="m12.5 14.5 2.5 2.5-2.5 2.5" />
    </Svg>
  );
}

export function IconClock(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 1.8" />
    </Svg>
  );
}

export function IconAlert(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 4.5 3.8 18.5h16.4z" />
      <path d="M12 10v3.5M12 16.2h.01" />
    </Svg>
  );
}

export function IconCheck(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8.4 12.2 2.4 2.4 4.8-5" />
    </Svg>
  );
}

export function IconArrowRight(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4.5 12h15M13.5 6.5 19.5 12l-6 5.5" />
    </Svg>
  );
}

export function IconChevronDown(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m6.5 9.5 5.5 5 5.5-5" />
    </Svg>
  );
}

export function IconMenu(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Svg>
  );
}

export function IconClose(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />
    </Svg>
  );
}

export function IconDocument(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M13.5 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8.5z" />
      <path d="M13.5 3.5V8a.5.5 0 0 0 .5.5h4.5" />
      <path d="M8.5 12.5h7M8.5 16h4.5" />
    </Svg>
  );
}

export function IconPlug(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M9 3.5v4M15 3.5v4" />
      <path d="M6.5 7.5h11v3.2a5.5 5.5 0 0 1-11 0z" />
      <path d="M12 16.2v4.3" />
    </Svg>
  );
}

export function IconScale(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 4v16M7 20h10" />
      <path d="M12 6.5 5 9M12 6.5 19 9" />
      <path d="M2.5 14 5 9l2.5 5a2.5 2.5 0 0 1-5 0Z" />
      <path d="M16.5 14 19 9l2.5 5a2.5 2.5 0 0 1-5 0Z" />
    </Svg>
  );
}

export function IconLayers(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m12 3.5 8.5 4.2L12 12 3.5 7.7z" />
      <path d="m3.5 12.3 8.5 4.2 8.5-4.2" />
      <path d="m3.5 16.6 8.5 4.2 8.5-4.2" />
    </Svg>
  );
}
