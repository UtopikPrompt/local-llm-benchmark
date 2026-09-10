import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      // Deploy the build/ folder to the `pages` branch (github-pages-deploy-action).
      pages: 'build',
      precompress: false,
      strict: false,
    }),
    // No server endpoints: this is a fully static, browser-only tool.
    prerender: {
      entries: ['*'],
    },
  },
};

export default config;
