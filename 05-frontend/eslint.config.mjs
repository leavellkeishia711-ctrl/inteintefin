import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "off", "no-restricted-syntax": [
        "error",
        {
          "selector": "CallExpression[callee.name='parseFloat']",
          "message": "parseFloat is forbidden as it causes precision loss with large Decimals. Use string manipulation or formatToParts with BigInt instead."
        },
        {
          "selector": "CallExpression[callee.name='parseInt']",
          "message": "parseInt is forbidden."
        },
        {
          "selector": "CallExpression[callee.name='Number']",
          "message": "Number() coercion is forbidden for the same reason."
        },
        {
          "selector": "UnaryExpression[operator='+']",
          "message": "Unary + coercion is forbidden."
        }
      ]
    }
  }
]);

export default eslintConfig;



