/** @type {import('prettier').Config} */
module.exports = {
  plugins: ['@ianvs/prettier-plugin-sort-imports'],
  printWidth: 100,
  semi: true,
  singleQuote: true,
  useTabs: false,
  tabWidth: 2,
  endOfLine: 'lf',
  trailingComma: 'es5',
  importOrderParserPlugins: ['typescript', 'jsx', 'decorators-legacy'],
  importOrder: [
    '<BUILTIN_MODULES>',
    '',

    '^(react/(.*)$)|^(react$)',
    '^(next/(.*)$)|^(next$)',
    '',

    '<THIRD_PARTY_MODULES>',
    '',

    // packages
    '^@workspace/ui', // Todo: fails sorting
    '',

    // app
    '^@/lib',
    '^@/app',
    '^@/actions',
    '^@/components',
    '^@/hooks',
    '^@/client',
    '^@/schemas',
    '^@/utils',
    '^@/constants',
    '^@/config',

    // relative
    '^[./]',
    '',

    // types
    '^@/types',
    '<TYPES>',
    '<TYPES>^[.]',
    '',

    // assets and styles
    '^@/assets',
    '^@/styles',
  ],
};
