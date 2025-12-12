/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './play.html',
    './author.html',
    './src/**/*.{svelte,js,ts}',
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [
      {
        dark: {
          ...require('daisyui/src/theming/themes')['dark'],
          'primary': '#0e639c',
          'primary-content': '#ffffff',
          'secondary': '#4ec9b0',
          'accent': '#dcdcaa',
          'neutral': '#2d2d2d',
          'base-100': '#1e1e1e',
          'base-200': '#252526',
          'base-300': '#2d2d2d',
          'base-content': '#d4d4d4',
          'info': '#569cd6',
          'success': '#4ec9b0',
          'warning': '#dcdcaa',
          'error': '#f14c4c',
        },
      },
    ],
    darkTheme: 'dark',
  },
}
