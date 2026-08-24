import { defineCollection } from 'astro:content';
import { z } from 'zod';
import { glob } from 'astro/loaders';

/**
 * Product catalogue. One markdown file per product in src/data/products/.
 * The frontmatter below is the full set of editable fields; the body of the
 * file becomes the long-form description on the product page.
 */
const products = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/data/products' }),
  schema: z.object({
    name: z.string(),
    /** Short line shown under the name in listings. No therapeutic claims. */
    summary: z.string(),
    category: z.enum(['Peptides', 'Blends', 'Cosmetic', 'Accessories']),
    /** Chemical Abstracts Service registry number, if one exists. */
    cas: z.string().optional(),
    molecularFormula: z.string().optional(),
    molecularWeight: z.string().optional(),
    sequence: z.string().optional(),
    /** e.g. "5mg" — the amount in a single vial. */
    vialSize: z.string(),
    /** e.g. "≥99%" — as stated on the certificate of analysis. */
    purity: z.string(),
    form: z.string().default('Lyophilised powder'),
    storage: z
      .string()
      .default('Store at -20°C. Protect from light. Reconstitute immediately before use.'),
    /** Price in GBP, excluding VAT and shipping. */
    price: z.number(),
    sku: z.string(),
    inStock: z.boolean().default(true),
    /** Surfaces the product on the homepage. */
    featured: z.boolean().default(false),
    /** Controls ordering within the catalogue; lower sorts first. */
    order: z.number().default(100),
  }),
});

export const collections = { products };
