#!/usr/bin/env node
/**
 * Generate `src/api/schema.d.ts` from the backend's OpenAPI document.
 *
 * The document is dumped by the backend (`make openapi`), so this script needs
 * no network and no running server. Every *response* property is marked required
 * because FastAPI always emits the full response object (`null` for absent
 * values): without this, a field carrying a Pydantic default arrives as optional
 * in TypeScript and every read needs a needless `?.`. Request bodies keep the
 * schema's own `required` list, so their optionality stays honest.
 *
 * Usage:
 *   node scripts/generate-api.mjs          # write src/api/schema.d.ts
 *   node scripts/generate-api.mjs --check  # fail if the file is stale (CI)
 */

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import openapiTS, { astToString } from "openapi-typescript";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const input = resolve(root, "openapi.json");
const output = resolve(root, "src/api/schema.d.ts");
const check = process.argv.includes("--check");

const document = JSON.parse(readFileSync(input, "utf8"));

const ast = await openapiTS(document, {
  alphabetize: true,
  transform(schemaObject, metadata) {
    if (String(metadata.path ?? "").endsWith("Request")) return;
    if (schemaObject.type === "object" && schemaObject.properties) {
      schemaObject.required = Object.keys(schemaObject.properties);
    }
  },
});

const generated = astToString(ast);

/** The banner is deterministic, but compare the body so a version bump is caught. */
const body = (text) => text.replace(/^\/\*\*[\s\S]*?\*\/\n/, "");

if (check) {
  const current = readFileSync(output, "utf8");
  if (body(current) !== body(generated)) {
    console.error("src/api/schema.d.ts is out of date. Run: make client");
    process.exit(1);
  }
  console.log("src/api/schema.d.ts is up to date");
} else {
  writeFileSync(output, generated);
  console.log(`generated ${output}`);
}
