import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { crx } from '@crxjs/vite-plugin'
import manifest from './manifest.json'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode === 'release' ? 'production' : mode, process.cwd(), '')
  const configuredManifest = structuredClone(manifest)
  if (mode === 'release') {
    const url = new URL(env.VITE_API_BASE_URL || 'http://localhost')
    if (url.protocol !== 'https:' || ['localhost', '127.0.0.1'].includes(url.hostname) || url.hostname.endsWith('example.com')) {
      throw new Error('Release builds require a real HTTPS VITE_API_BASE_URL in .env.production')
    }
    configuredManifest.host_permissions = configuredManifest.host_permissions.filter(origin => !origin.includes('localhost') && !origin.includes('127.0.0.1'))
  }
  if (env.VITE_API_BASE_URL) {
    const apiOrigin = new URL(env.VITE_API_BASE_URL).origin
    const permission = `${apiOrigin}/*`
    if (!configuredManifest.host_permissions.includes(permission)) {
      configuredManifest.host_permissions.push(permission)
    }
  }
  return {
    define: { 'import.meta.env.VITE_API_BASE_URL': JSON.stringify(env.VITE_API_BASE_URL || 'http://127.0.0.1:8000') },
    plugins: [react(), crx({ manifest: configuredManifest })],
  }
})
