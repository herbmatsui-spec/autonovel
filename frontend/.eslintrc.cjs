const tseslint = require("@typescript-eslint/eslint-plugin");
const tsParser = require("@typescript-eslint/parser");
const reactPlugin = require("eslint-plugin-react");
const reactHooks = require("eslint-plugin-react-hooks");
const a11y = require("eslint-plugin-jsx-a11y");
const testingLibrary = require("eslint-plugin-testing-library");

module.exports = [
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
        ecmaFeatures: { jsx: true },
        project: "./tsconfig.json",
      },
      globals: {
        document: "readonly",
        window: "readonly",
        navigator: "readonly",
        URL: "readonly",
        Blob: "readonly",
        fetch: "readonly",
      },
    },
    plugins: {
      "@typescript-eslint": tseslint,
      react: reactPlugin,
      "react-hooks": reactHooks,
      "jsx-a11y": a11y,
      "testing-library": testingLibrary,
    },
    rules: {
      "react/react-in-jsx-scope": "off",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "jsx-a11y/label-has-associated-control": "off",
      "testing-library/prefer-screen-queries": "warn",
      "testing-library/await-async-events": "warn",
    },
    settings: {
      react: { version: "18.2" },
    },
  },
];
