import js from '@eslint/js';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';

// ─── Browser globals (DOM API types used in shadcn/ui components) ─────────────
// The `globals` npm package is not installed here; we enumerate the subset
// that appears in our component tree.  Add as needed.
const browserGlobals = {
  // Fetch / network
  RequestInit: 'readonly',
  RequestInfo: 'readonly',
  RequestCredentials: 'readonly',
  HeadersInit: 'readonly',
  BodyInit: 'readonly',
  // HTML element interfaces used in Radix/shadcn component forwardRef types
  HTMLElement: 'readonly',
  HTMLDivElement: 'readonly',
  HTMLButtonElement: 'readonly',
  HTMLInputElement: 'readonly',
  HTMLTextAreaElement: 'readonly',
  HTMLSelectElement: 'readonly',
  HTMLLabelElement: 'readonly',
  HTMLSpanElement: 'readonly',
  HTMLParagraphElement: 'readonly',
  HTMLHeadingElement: 'readonly',
  HTMLUListElement: 'readonly',
  HTMLOListElement: 'readonly',
  HTMLLIElement: 'readonly',
  HTMLAnchorElement: 'readonly',
  HTMLImageElement: 'readonly',
  HTMLFormElement: 'readonly',
  HTMLTableElement: 'readonly',
  HTMLTableSectionElement: 'readonly',
  HTMLTableRowElement: 'readonly',
  HTMLTableCellElement: 'readonly',
  HTMLTableCaptionElement: 'readonly',
  // SVG
  SVGSVGElement: 'readonly',
  SVGElement: 'readonly',
  // Misc DOM
  MouseEvent: 'readonly',
  KeyboardEvent: 'readonly',
  FocusEvent: 'readonly',
  Event: 'readonly',
  EventTarget: 'readonly',
  Element: 'readonly',
  Node: 'readonly',
  Document: 'readonly',
  Window: 'readonly',
  MutationObserver: 'readonly',
  IntersectionObserver: 'readonly',
  ResizeObserver: 'readonly',
  CustomEvent: 'readonly',
  DOMRect: 'readonly',
};

// ─── Node.js globals (vitest.config.ts, next.config.js, scripts) ─────────────
const nodeGlobals = {
  __dirname: 'readonly',
  __filename: 'readonly',
  require: 'readonly',
  module: 'readonly',
  exports: 'readonly',
  Buffer: 'readonly',
  global: 'readonly',
  process: 'readonly',
};

export default [
  {
    ignores: [
      '.next/**',
      'node_modules/**',
      'next-env.d.ts',
      'public/**',
      'tests/.playwright-report/**',
    ],
  },
  js.configs.recommended,
  // ─── TypeScript source files (app + lib + components) ─────────────────────
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
      globals: {
        React: 'readonly',
        JSX: 'readonly',
        process: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        Request: 'readonly',
        Response: 'readonly',
        Headers: 'readonly',
        FormData: 'readonly',
        Blob: 'readonly',
        AbortController: 'readonly',
        AbortSignal: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        ...browserGlobals,
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      ...tsPlugin.configs.strict.rules,
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { prefer: 'type-imports', fixStyle: 'inline-type-imports' },
      ],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      // Allow Promise<void> and similar generic void usages (common in API
      // return types; the strict default bans void in generic positions).
      '@typescript-eslint/no-invalid-void-type': [
        'error',
        { allowInGenericTypeArguments: true },
      ],
      'no-console': ['warn', { allow: ['warn', 'error', 'info'] }],
      'no-unused-vars': 'off',
    },
  },
  // ─── Config files (vitest.config.ts, next.config.js, tailwind.config.*) ───
  // These run in Node.js via the build tool, not in the browser.
  {
    files: [
      '*.config.{ts,js,mjs}',
      'vitest.config.ts',
      'playwright.config.ts',
    ],
    languageOptions: {
      globals: {
        ...nodeGlobals,
      },
    },
  },
  // ─── Test files — relax rules that are noisy in test code ─────────────────
  {
    files: [
      'src/**/*.test.{ts,tsx}',
      'tests/**/*.{ts,tsx}',
    ],
    rules: {
      // Non-null assertions are common in tests after expect().toBeDefined()
      // guards; the assertion is logically sound there.
      '@typescript-eslint/no-non-null-assertion': 'off',
      // Playwright tests commonly import fixtures without using all of them
      // in every test file.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
];
