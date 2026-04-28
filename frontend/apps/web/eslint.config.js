import { nextJsConfig } from "@workspace/eslint-config/next-js"

/** @type {import("eslint").Linter.Config} */
export default [
  {
    ignores: [
      "**/.next/**",
      "**/node_modules/**",
      "**/dist/**",
      // Hey API codegen — do not hand-edit or lint-check
      "src/client/**",
    ],
  },
  ...nextJsConfig,
  {
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
          destructuredArrayIgnorePattern: '^_',
        },
      ],
      // Known-safe patterns with react-hook-form, TanStack Table, etc. (React Compiler heuristics)
      'react-hooks/incompatible-library': 'off',
      // Legitimate patterns (modal reset, delayed UI) still use setState from effects
      'react-hooks/set-state-in-effect': 'off',
    },
  },
]
