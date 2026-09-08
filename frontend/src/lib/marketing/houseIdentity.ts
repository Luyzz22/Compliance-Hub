/**
 * Herkunft und Produktfamilie — eine Quelle für alle öffentlichen Flächen.
 *
 * Compliance Hub ist nicht das einzige Produkt seines Hauses. Wer von
 * NormPilot Industrie kommt, soll dieselbe Handschrift wiedererkennen, und wer
 * hier beginnt, soll die Schwesteranwendung finden. Beides sind Aussagen über
 * reale Unternehmen und reale Produkte und gehören deshalb an *eine* Stelle,
 * nicht in Marketingcopy verstreut.
 *
 * Was hier bewusst NICHT steht: die Firmierung mit Rechtsformzusatz, Anschrift,
 * Registerangaben. Diese Angaben kommen ausschließlich aus `getLegalConfig()`
 * und damit aus der geprüften Umgebungskonfiguration des Impressums. Eine
 * Firmierung, die hier als Literal stünde, könnte dem eigenen Impressum
 * widersprechen — auf einer Seite, deren ganzes Argument Nachweisbarkeit ist,
 * wäre das der teuerste denkbare Fehler. `houseIdentity.test.ts` hält das fest.
 *
 * Ebenso wenig gehören hierher: Zertifizierungen, Serverstandorte,
 * Datenresidenz oder Konformitätszusagen.
 */
export const HOUSE = {
  /** Dachmarke als Absender, ohne Rechtsformzusatz — die Firmierung steht im Impressum. */
  name: "SBS Deutschland",
  corporateUrl: "https://sbsdeutschland.com",
  /** Die Firmierung ist im Impressum zu finden, nicht in dieser Datei. */
  imprintHref: "/impressum",
} as const;

export type SisterProduct = {
  name: string;
  /** Ein Satz, der die Abgrenzung erklärt — nicht das Produkt bewirbt. */
  scope: string;
  href: string;
};

/**
 * Schwesterprodukte desselben Hauses.
 *
 * Die Beschreibung grenzt ab, statt zu werben: Leserinnen und Leser sollen in
 * einem Satz erkennen, ob sie hier oder dort richtig sind. Ein zweiter
 * Werbetext wäre an dieser Stelle Reibung, kein Nutzen.
 */
export const SISTER_PRODUCTS: readonly SisterProduct[] = [
  {
    name: "NormPilot Industrie",
    scope:
      "Normkonformität und Audit-Evidenz für Fertigung und Produktdokumentation",
    href: "https://www.normpilot-industrie.de",
  },
] as const;
