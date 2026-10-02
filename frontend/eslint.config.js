import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

/**
 * Flat ESLint config.
 *
 * The point of interest is `@typescript-eslint/no-deprecated`: it is a type-aware
 * rule, so it turns a deprecation in the React (or DOM) types into a build failure
 * instead of an editor squiggle. That is exactly how `React.FormEvent` - deprecated
 * in the React 19 types - was found.
 */
export default tseslint.config(
  {
    ignores: [
      "dist/**",
      "coverage/**",
      "playwright-report/**",
      "test-results/**",
      "node_modules/**",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser, ...globals.node },
      parserOptions: {
        // Type-aware linting, resolved from the nearest tsconfig.
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // `exhaustive-deps` ships as a warning; a missing dependency is a bug, not a
      // suggestion, so it is promoted here.
      "react-hooks/exhaustive-deps": "error",
      // The remaining react-hooks rules are React Compiler diagnostics. This app
      // does not opt into the compiler, and it fetches data in an effect (the
      // documented fallback when there is no data library or Suspense). That
      // pattern is flagged by `set-state-in-effect`, so it is disabled with the
      // reason recorded rather than silenced line by line. `InsightPanel` still
      // prefers the idiomatic remount (`key`) over resetting state in an effect.
      "react-hooks/set-state-in-effect": "off",
      "@typescript-eslint/no-deprecated": "error",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/consistent-type-imports": [
        "error",
        { prefer: "type-imports" },
      ],
    },
  },
  {
    // Tests and specs may use the non-null assertion to keep fixtures readable.
    files: ["src/test/**/*.{ts,tsx}", "e2e/**/*.ts"],
    rules: { "@typescript-eslint/no-non-null-assertion": "off" },
  },
);
