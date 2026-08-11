#!/usr/bin/env node

import { readFileSync, readdirSync, statSync } from "node:fs";
import { extname, resolve } from "node:path";

const ignoredDirectories = new Set([
  ".git",
  ".next",
  "coverage",
  "dist",
  "node_modules",
  "output",
]);
const supportedExtensions = new Set([
  ".css",
  ".html",
  ".js",
  ".jsx",
  ".mdx",
  ".ts",
  ".tsx",
]);

const args = process.argv.slice(2);
const json = args.includes("--json");
const targets = args.filter((argument) => argument !== "--json");

if (targets.length === 0) {
  process.stderr.write(
    "Usage: frontend_design_audit.mjs [--json] <file-or-directory> [...]\n",
  );
  process.exit(1);
}

function collect(path, files) {
  const absolute = resolve(path);
  const stat = statSync(absolute);

  if (stat.isDirectory()) {
    for (const entry of readdirSync(absolute, { withFileTypes: true })) {
      if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue;
      collect(resolve(absolute, entry.name), files);
    }
    return;
  }

  if (supportedExtensions.has(extname(absolute))) files.add(absolute);
}

function lineNumber(source, index) {
  return source.slice(0, index).split("\n").length;
}

function addMatches(findings, file, source, rule) {
  for (const match of source.matchAll(rule.pattern)) {
    if (rule.test && !rule.test(match)) continue;
    findings.push({
      rule: rule.id,
      severity: rule.severity,
      file,
      line: lineNumber(source, match.index ?? 0),
      message: rule.message,
      snippet: match[0].slice(0, 160),
    });
  }
}

const rules = [
  {
    id: "visible-dash",
    severity: "review",
    pattern: /[—–]/gu,
    message: "Review em or en dash usage in visible interface copy.",
  },
  {
    id: "pill-default",
    severity: "advisory",
    pattern: /\brounded-full\b/gu,
    message: "Confirm that a pill shape is semantically necessary.",
  },
  {
    id: "uppercase-microcopy",
    severity: "advisory",
    pattern: /\buppercase\b/gu,
    message: "Review uppercase utility classes for ornamental micro-labels.",
  },
  {
    id: "transition-all",
    severity: "advisory",
    pattern: /\btransition-all\b/gu,
    message: "Transition explicit properties instead of using transition-all.",
  },
  {
    id: "tight-tracking",
    severity: "advisory",
    pattern: /tracking-\[(-?\d+(?:\.\d+)?)em\]/gu,
    test: (match) => Number(match[1]) < -0.04,
    message: "Letter spacing is tighter than the -0.04em enterprise display floor.",
  },
  {
    id: "oversized-display",
    severity: "advisory",
    pattern: /text-\[(\d+(?:\.\d+)?)rem\]/gu,
    test: (match) => Number(match[1]) > 6,
    message: "Display type exceeds 96px and needs an explicit product reason.",
  },
];

const files = new Set();
try {
  for (const target of targets) collect(target, files);
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
}

const findings = [];
for (const file of [...files].sort()) {
  const source = readFileSync(file, "utf8");
  for (const rule of rules) addMatches(findings, file, source, rule);

  const gradients = source.match(/linear-gradient\(/gu)?.length ?? 0;
  if (gradients >= 2 && /background-size:\s*\d+px\s+\d+px/gu.test(source)) {
    findings.push({
      rule: "decorative-grid",
      severity: "advisory",
      file,
      line: lineNumber(source, source.search(/linear-gradient\(/u)),
      message: "Review a tiled two-axis gradient for decorative generated-UI styling.",
      snippet: "multiple linear gradients with a fixed background-size",
    });
  }
}

const result = {
  filesScanned: files.size,
  findings,
  summary: findings.reduce(
    (summary, finding) => ({
      ...summary,
      [finding.severity]: (summary[finding.severity] ?? 0) + 1,
    }),
    {},
  ),
};

if (json) {
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} else if (findings.length === 0) {
  process.stdout.write(`Frontend design audit passed (${files.size} files).\n`);
} else {
  for (const finding of findings) {
    process.stdout.write(
      `${finding.severity.toUpperCase()} ${finding.file}:${finding.line} ${finding.rule}: ${finding.message}\n`,
    );
  }
  process.stdout.write(`Found ${findings.length} review item(s) in ${files.size} files.\n`);
}

process.exit(findings.length === 0 ? 0 : 2);
