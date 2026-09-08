---
version: beta
name: Compliance Hub — Blue-Brass Evidence
description: Die öffentliche Fläche von complywithai.de. Eine Handschrift mit NormPilot Industrie, ausgeführt mit der Beweisführung einer Beratungsvorlage.
house: SBS Deutschland
sibling: NormPilot Industrie (normpilot-industrie.de)
colors:
  brand: "#003856"
  brand-hover: "#002A42"
  brand-600: "#0E4D6E"
  brass: "#B98F42"
  brass-ink: "#8A6626"
  stage: "#00182A"
  stage-raised: "#001F35"
  stage-panel: "#00243C"
  stage-panel-soft: "#001D31"
  canvas: "#F5F8F9"
  surface: "#FFFFFF"
  ink: "#161E23"
  ink-soft: "#38444C"
  ink-muted: "#4E5C65"
  ink-faint: "#61717C"
  line: "#DDE5E9"
  line-strong: "#C3CFD6"
  cta-on-stage: "#B98F42"
  cta-on-stage-ink: "#0C1216"
  state-ok: "#0F6E4E"
  state-warn: "#8A5A0B"
  state-crit: "#A32217"
  state-ok-on-stage: "#6CC9A2"
  state-warn-on-stage: "#E5B45F"
  state-crit-on-stage: "#F0A49A"
typography:
  display:
    fontFamily: "SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: clamp(2.15rem, 1.5rem + 2.35vw, 3.4rem)
    fontWeight: 620
    lineHeight: 1.05
    letterSpacing: -0.032em
  heading-lg:
    fontSize: clamp(1.95rem, 1.45rem + 1.8vw, 2.9rem)
    fontWeight: 620
    lineHeight: 1.08
    letterSpacing: -0.032em
  heading-md:
    fontSize: clamp(1.7rem, 1.3rem + 1.45vw, 2.4rem)
    fontWeight: 620
    lineHeight: 1.14
    letterSpacing: -0.022em
  heading-sm:
    fontSize: clamp(1.2rem, 1.08rem + 0.5vw, 1.45rem)
    fontWeight: 620
    lineHeight: 1.28
  lead:
    fontSize: clamp(1rem, 0.96rem + 0.22vw, 1.125rem)
    lineHeight: 1.65
    maxWidth: 62ch
  body:
    fontSize: 0.9375rem
    lineHeight: 1.7
  eyebrow:
    fontSize: 0.6875rem
    fontWeight: 660
    letterSpacing: 0.14em
    textTransform: uppercase
    mark: brass hairline, 24px, via ::before
  technical-label:
    fontFamily: "SFMono-Regular, Cascadia Code, ui-monospace, monospace"
    fontSize: 0.6875rem
    fontVariantNumeric: tabular-nums
rounded:
  none: 0px
  xs: 4px
  sm: 6px
  control: 8px
  surface: 12px
  media: 16px
spacing:
  hairline: 1px
  micro: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  section: clamp(4rem, 2.6rem + 4.4vw, 7rem)
  section-tight: clamp(2.75rem, 2rem + 2.4vw, 4.5rem)
  page-gutter-mobile: 20px
  page-gutter-desktop: 32px
  max-width: 78rem
components:
  stage:
    backgroundColor: "{colors.stage}"
    textColor: "#DDE5E9"
    note: Autoritätsfläche. Hero, Abschluss-CTA, Kopf- und Fußzeile.
  paper:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    note: Arbeitsfläche und Unterlage auf der Bühne.
  mat:
    border: "1px solid rgba(185,143,66,0.30)"
    rounded: "{rounded.surface}"
    padding: 12px
    note: Passepartout um eine helle Unterlage auf der Bühne.
  button-primary-on-paper:
    backgroundColor: "{colors.brand}"
    textColor: "#FFFFFF"
    height: 44px
  button-primary-on-stage:
    backgroundColor: "{colors.cta-on-stage}"
    textColor: "{colors.cta-on-stage-ink}"
    height: 44px
    note: Die einzige Messingfläche des Systems.
  button-secondary:
    backgroundColor: transparent
    border: "1px solid {colors.line-strong}"
    hoverBorder: "{colors.brass}"
    height: 44px
  brass-rule:
    height: 1px
    backgroundImage: linear-gradient auslaufend zu beiden Seiten
  exhibit:
    index: mono, brass, tabular-nums
    claim: Kernaussage, nicht Thema
    source: Lesart / Grundlage / Quelle unter der Abbildung
  rail:
    gap: 1px
    backgroundColor: "{colors.line}"
    note: Eine Fläche, geteilt durch Haarlinien — keine Kachelreihe.
---

# Compliance Hub — Blue-Brass Evidence

## Herkunft

Compliance Hub und NormPilot Industrie stammen aus demselben Haus. Bis zu dieser
Ebene sah man das nicht: NormPilot lief auf Petrol-Navy mit Messing, Compliance
Hub auf einem eigenständigen Indigo (`#3f63ea`) über bläulichen Slate-Flächen.
Zwei Produkte desselben Anbieters wirkten wie zwei Anbieter.

Diese Ebene führt beide zusammen. Der Anker ist `#003856` — exakt der Wert, den
NormPilot als `brand-700` führt. Übernommen sind außerdem die kühl-neutrale
Graphitskala statt der Slates, die Messing-Haarlinie als einziger
Autoritätsakzent, die Regel „Messing ist Linie, nie Fläche" samt ihrer einen
Ausnahme, das Blueprint-Raster und die Bühnen-/Unterlagen-Polarität.

Was Compliance Hub darüber hinaus trägt, ist die **Beweisführung**. NormPilot
zeigt ein Werkzeug; Compliance Hub führt ein Argument. Dafür gibt es die
Exhibit-Ebene (siehe unten) — die Handschrift einer Beratungsvorlage, nicht die
einer Broschüre.

## Bühne und Unterlage

Das System kennt zwei Belegungen derselben Rollen:

- **`.mk-stage`** — dunkles Petrol-Navy mit Messingkanten. Hero, Abschluss-CTA,
  Kopf- und Fußzeile. Die Bühne ist die Ausnahme mit Begründung, nicht der
  Normalfall: sie trägt Autorität, keine Fließtexte.
- **`.mk-scope` / `.mk-paper`** — helle Arbeitsfläche. Der Grundzustand, weil
  dort gelesen wird. `.mk-paper` schaltet die Rollen *innerhalb* der Bühne
  zurück auf hell.

Diagramme, Tabellen und Produktansichten sind inhaltlich Dokumente. Sie werden
für die Bühne nicht neu gezeichnet, sondern als **Unterlage** in ein
Passepartout gelegt (`.mk-mat` + `.mk-paper`). Der Grund ist nicht Geschmack:
1px-Linien, Statusfarben und Monospace-Locator sind auf Weiß kalibriert.

Komponenten lesen ausschließlich die Rollen (`--mk-fg`, `--mk-panel`, `--mk-cta`
…) und wissen nie, auf welchem Grund sie liegen. Es gibt keinen zweiten Satz
Klassen und kein `inverse`-Prop.

## Farbe

Petrol-Navy ist die Marke und zugleich der Interaktionsakzent. Messing ist
**Linie, Marke und Icon — nie Fläche**. Genau eine Ausnahme trägt das System,
und es ist die Primäraktion auf der dunklen Bühne: eine Seite voller
Goldflächen kippt ins Dekorative, aber Weiß auf Navy stand neben ebenfalls
hellen Panelflächen und war als *die* Handlung der Seite nicht mehr erkennbar.
`brass-400` auf `slate-950`-Schrift erreicht 6,3:1 und trägt damit AA auch für
Kleintext.

Grün, Amber und Rot erscheinen nur, wenn ein echter Produktstatus sie braucht.
Sie liegen in zwei Sätzen vor — auf Weiß kalibriert und für die Bühne
aufgehellt — weil eine einzige Statusfarbe auf beiden Gründen entweder zu hell
oder zu dunkel ist. Farbe ist nie alleiniger Informationsträger.

Kontrast: Fließtext erreicht auf beiden Belegungen mindestens 4,5:1;
`src/test/marketingDesignSystem.test.ts` rechnet das aus den Tokens nach und
schlägt fehl, wenn ein Wert darunter rutscht.

## Typografie

SF Pro als Systemschrift, ohne externe Font-Abhängigkeit. Überschriften mit
Gewicht 620 und enger, kontrollierter Laufweite. Fließtext zwischen 55 und
70 Zeichen je Zeile.

**Eyebrow-Labels sind Teil dieses Systems** (die Vorgängerfassung schloss sie
aus). Sie tragen den Messingstrich der Marke als `::before` — im Markup läge er
irgendwann nicht mehr überall. Genau eine `h1` pro Seite, Überschriften ohne
Ebenensprung.

Zahlen stehen spaltentreu (`tabular-nums`); Control-Namen, Locator und
Evidenz-Metadaten stehen im Monospace-Satz.

## Exhibit-Ebene

Der Teil dieser Website, der eine Abbildung von einer Illustration
unterscheidet. Jede Abbildung trägt:

1. **Eine Nummer** — „Exhibit 4" lässt sich in einer Sitzung benennen, „die
   Grafik weiter unten" nicht. Lückenlos ab 1, je Seite.
2. **Eine Kernaussage als Titel** — die *Aussage*, nicht das Thema: „Eine
   gepflegte Risikobeurteilung bedient sechs Nachweispflichten" statt „Control
   Mapping".
3. **Eine Quellenzeile** unter der Abbildung: Lesart, Grundlage, Quelle. Sie
   steht unten, weil sie erklärt, was zu sehen ist, und erst nach dem Bild
   gebraucht wird.

**Prüfbedingung:** Wer die Seite überfliegt und nur die Exhibit-Titel liest,
hat das vollständige Argument. Trifft das nicht zu, ist der Titel falsch
formuliert.

Kennzahlen (`KeyFigure`) tragen ihre Grundlage als Pflichtfeld. Eine Zahl ohne
benennbare Quelle steht nicht auf dieser Seite.

## Layout

Fluid bis 78rem, 20px mobile und 32px Desktop-Gutter. Sektionsrhythmus über ein
Token, nicht über Einzelklassen. Erzählungen sind asymmetrisch: eine knappe
Aussage neben genau einem erklärenden Artefakt, beide oben ausgerichtet.

Beziehungen werden zuerst über Linien und ausgerichtete Reihen ausgedrückt,
erst dann über Karten. Mehrere kurze Aussagen gehören in *eine* geteilte Fläche
(`.mk-rail`, `gap: 1px` auf der Linienfarbe) — eine Kachelreihe liest sich als
Badge-Wand, eine geteilte Fläche als Leiste eines Geräts.

Kein horizontales Scrollen bei 375, 768, 1024 und 1440px.

## Tiefe, Form, Bewegung

Hierarchie entsteht aus Tonwerten, Weißraum und 1px-Linien. Schatten bleiben
auf Hero-Visual, Produktansicht und Abschlussfläche beschränkt. Blur nur auf
der klebenden Kopfzeile.

Das **Blueprint-Raster** ist zugelassen (die Vorgängerfassung schloss
dekorative Raster aus): sehr flach, zu den Kanten ausmaskiert, hinter dem
Inhalt, ohne Klickfläche. Fällt es aus, bleibt die Sektion vollständig lesbar.
Leuchtende Orbs, Glass-Panels und Ambient-Verläufe bleiben ausgeschlossen.

Radien: 8px für Controls, 12px für Flächen, 16px für Medien. Strukturzeilen
bleiben eckig. Pillen sind kein Standardcontainer.

**Motion-Governance.** Bewegung ist erlaubt, wenn sie Produktlogik oder
Informationshierarchie erklärt — nie als Dekoration.

- Nur `transform` und `opacity`.
- Scroll-Reveal über `view()`, ohne JavaScript; der Ruhezustand ist sichtbar,
  Inhalte können nie dauerhaft unsichtbar bleiben.
- Die einzige Hover-Geste ist `.mk-card-interactive`: zwei Pixel Anhebung, eine
  Messingkante, nur bei `hover: hover` und `pointer: fine`.
- Keine endlosen Schleifen, kein Scroll-Jacking, keine Motion-Bibliotheken.
- Unter `prefers-reduced-motion` bleibt kein Rest von Bewegung.

## Chrome und Herkunft

Die Wortmarke ist ein Geschwister der NormPilot-Marke: gleiches Schild in
Petrol-Navy, gleiche drei Registerlinien, gleiches Messingsiegel unten rechts.
Das Siegel trägt ein Häkchen statt einer Lupe — NormPilot prüft, Compliance Hub
belegt. Gleiche Familie, andere Handlung.

Die aktive Route wird mit einem Messingstrich markiert, nicht mit einer grauen
Fläche — dieselbe Marke wie am Eyebrow.

Der Footer trägt ein **Herkunftsband**: Dachmarke, Schwesterprodukt und der
Verweis auf das Impressum. Die Firmierung mit Rechtsformzusatz, Anschrift und
Registerangaben stehen ausschließlich im Impressum und kommen aus
`getLegalConfig()`. Eine zweite, handgepflegte Fassung in der Marketingcopy
könnte dem eigenen Impressum widersprechen — auf einer Seite, deren ganzes
Argument Nachweisbarkeit ist, wäre das der teuerste denkbare Fehler.
`src/lib/marketing/houseIdentity.test.ts` hält das fest.

## Do's and Don'ts

- Evidenz, Grenzen und Prüfverantwortung stehen neben der Aussage, die sie
  qualifizieren.
- Eine dominante Aktion je Sichtbereich; wiederkehrende Aktionslabels bleiben
  identisch.
- Der öffentliche Release bleibt zustandslos; Azure OpenAI und die
  Enterprise-Datenebene werden als gated beschrieben, solange keine datierte
  Evidenz vorliegt.
- Keine erfundenen Kunden, Logos, Zertifizierungen, Benchmarks, Prozentwerte
  oder Testimonials.
- Keine Darstellung von Rechtsauslegung, Risikoklassifizierung oder
  Freigabeentscheidung als automatische Systementscheidung.
- Verbotene Claims: „revolutionär", „vollautomatisch", „100 % konform",
  „zertifiziert", „garantiert".
- Keine generischen Drei-Karten-Raster, keine Badge-Wände, keine dekorativen
  Dashboards.
- Keine zwei konkurrierenden Designsysteme auf derselben Website: die
  öffentliche Fläche nutzt ausschließlich die `mk-*`-Rollen, keine rohen
  Tailwind-Paletten.

### Zum Gedankenstrich

Die Vorgängerfassung untersagte Halbgeviert- und Geviertstriche in sichtbarer
Oberflächentexte. Die deutschsprachige Copy hielt sich durchgehend nicht daran,
und zu Recht: im Deutschen ist der Gedankenstrich die korrekte Auszeichnung für
den Einschub, wofür das Englische das Komma oder die Klammer nutzt. Die Regel
stammte aus einer englischsprachigen Vorlage. Sie gilt hier nicht mehr;
stattdessen: Gedankenstrich mit Leerzeichen, sparsam, nie als Ersatz für einen
Punkt.
