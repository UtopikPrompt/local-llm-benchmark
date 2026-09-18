import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./setup-test.js'],
    workspace: {
      projects: [
        {
          name: 'python',
          test: {
            include: ['**/*.py']
          },
          workspace: './'
        },
        {
          name: 'js',
          test: {
            include: ['tests/**/*.test.js', 'tests/**/*.spec.js']
          },
          workspace: './'
        }
      ]
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['**/*.py', '**/*.js'],
      exclude: ['**/node_modules/**', '**/*.min.js'],
    },
    testTimeout: 10000,
    hookTimeout: 5000
  },
  resolve: {
    alias: {
      '@': '/src'
    }
  }
})
