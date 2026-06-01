import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser
    },
    plugins: {
      "react-hooks": reactHooks
    },
    rules: {
      ...reactHooks.configs.recommended.rules
    }
  },
  {
    files: ["src/main/preload.cjs"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.node,
      sourceType: "commonjs"
    },
    rules: {
      "@typescript-eslint/no-require-imports": "off"
    }
  }
);
