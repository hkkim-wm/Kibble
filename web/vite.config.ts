import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  // @ts-expect-error -- vitest injects the `test` property at runtime
  test: {
    environment: 'jsdom',
  },
})
