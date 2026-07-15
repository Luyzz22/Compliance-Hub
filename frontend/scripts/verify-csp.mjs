import { readFileSync, readdirSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";

const errors = [];
const sourceRoot = resolve("src");
const sourceExtensions = new Set([".js", ".jsx", ".mjs", ".ts", ".tsx"]);

function scan(directory) {
  for (const entry of readdirSync(directory)) {
    const path = join(directory, entry);
    const metadata = statSync(path);
    if (metadata.isDirectory()) {
      scan(path);
      continue;
    }
    if (!sourceExtensions.has(extname(path)) || path.includes(".test.")) continue;

    const content = readFileSync(path, "utf8");
    if (/\bstyle\s*=/.test(content)) {
      errors.push(`${path}: React inline style attributes are forbidden by the strict CSP`);
    }
    if (/\bdangerouslySetInnerHTML\s*=/.test(content)) {
      errors.push(`${path}: dangerouslySetInnerHTML requires explicit security adjudication`);
    }
    if (content.includes("unsafe-inline")) {
      errors.push(`${path}: CSP unsafe-inline bypass is forbidden`);
    }
  }
}

scan(sourceRoot);

const nextConfig = readFileSync(resolve("next.config.ts"), "utf8");
if (nextConfig.includes("Content-Security-Policy")) {
  errors.push("next.config.ts: CSP must be generated per request in proxy.ts, not statically");
}

if (errors.length) {
  process.stderr.write(`Strict CSP verification failed:\n- ${errors.join("\n- ")}\n`);
  process.exit(1);
}

process.stdout.write("Strict CSP verification passed\n");
