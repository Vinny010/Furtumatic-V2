// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  site: 'https://vippeptides.co.uk',
  trailingSlash: 'ignore',
  build: { format: 'directory' },
  integrations: [
    sitemap({
      // The enquiry list is per-visitor and the 404 is not a destination.
      filter: (page) => !page.includes('/enquiry'),
    }),
  ],
});
