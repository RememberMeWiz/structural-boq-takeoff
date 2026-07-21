/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Drafting-desk palette: dark canvas for the drawing viewer,
        // cool paper for data panels (deliberately not the warm-cream default).
        canvas: {
          900: '#0d1117',
          800: '#141b23',
          700: '#1c2530',
          600: '#2a3644',
          500: '#3d4c5e'
        },
        paper: {
          50: '#f6f7f5',
          100: '#eef0ec',
          200: '#dde1d9'
        },
        ink: {
          900: '#141a17',
          700: '#3a453f',
          500: '#69756e'
        },
        // Confidence scale: low (unverified, needs review) -> high (trusted)
        conf: {
          low: '#c4501f',
          mid: '#d9a441',
          high: '#3f8a5c'
        },
        // Divergence flag colors, distinct from confidence colors on purpose
        flag: {
          ok: '#3f8a5c',
          warn: '#c4501f'
        },
        brass: '#a9772f'
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        sans: ['"Inter"', 'ui-sans-serif', 'system-ui', 'sans-serif']
      }
    }
  },
  plugins: []
}
