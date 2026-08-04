import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

/**
 * Build-time guard for VITE_API_URL.
 *
 * The frontend has no runtime configuration: the API origin is substituted into
 * the bundle by `vite build` and then uploaded to S3, so a build with the
 * variable unset produces an artifact that can never reach the backend. Catching
 * that here — while the build is still running, before anything is uploaded — is
 * the only place the failure is cheap. `src/api/client.js` also throws, but that
 * throw is bundled and only fires in the visitor's browser, which means a broken
 * deploy is already live by the time anyone finds out.
 *
 * Skipped for `vite dev` and for an explicit `--mode development` build, which
 * mirrors `import.meta.env.DEV`: in dev the frontend calls /api same-origin and
 * Vite proxies to Flask, so no origin is needed.
 */
function assertApiUrl(mode) {
  // loadEnv merges .env files with matching process.env vars, so this sees the
  // value however CI or the deploy workflow supplies it.
  const { VITE_API_URL } = loadEnv(mode, process.cwd())
  const value = (VITE_API_URL || '').trim()

  if (!value) {
    throw new Error(
      'VITE_API_URL is not set.\n' +
        'A production build bakes the API origin into the bundle, so building ' +
        'without it would ship a frontend that cannot reach the backend.\n' +
        'Set it for the build, e.g.\n' +
        '  VITE_API_URL=https://api.asktheearlychurch.com npm run build\n' +
        'For a local development build instead, use: vite build --mode development',
    )
  }

  let parsed
  try {
    parsed = new URL(value)
  } catch {
    throw new Error(
      `VITE_API_URL is not a valid absolute URL: ${value}\n` +
        'It must include the scheme, e.g. https://api.asktheearlychurch.com',
    )
  }
  if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
    throw new Error(
      `VITE_API_URL must be an http(s) URL, got: ${value}`,
    )
  }
}

export default defineConfig(({ command, mode }) => {
  if (command === 'build' && mode !== 'development') assertApiUrl(mode)

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': 'http://127.0.0.1:5001',
      },
    },
    test: {
      environment: 'jsdom',
      include: ['src/**/*.test.{js,jsx}'],
      setupFiles: ['./src/test-setup.js'],
      globals: false,
    },
  }
})
