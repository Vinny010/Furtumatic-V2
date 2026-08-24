# vippeptides.co.uk

Marketing and catalogue site for VIP Peptides, a UK supplier of research-grade peptides.

Built with [Astro](https://astro.build) as a fully static site: no server, no database, no runtime
dependencies. It can be hosted free on Cloudflare Pages, Netlify or GitHub Pages.

---

## Quick start

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # type-checks, then outputs to dist/
npm run preview  # serve the built site locally
```

Requires Node 20 or newer.

---

## Editing the site

Almost everything a non-developer needs is in two places.

### 1. Business details — `src/config.ts`

Company name, registration number, VAT number, address, contact emails, opening hours, and the
form endpoint. Nothing else in the codebase hardcodes these, so changing them here updates the
whole site including the legal pages and the footer.

The values currently marked `TBC` (company number, VAT number, address) are placeholders. The
footer hides each one until it is filled in, so nothing incorrect is displayed in the meantime.

### 2. Products — `src/data/products/*.md`

One markdown file per product. The frontmatter is the product data; the text below it becomes the
long description on the product page.

```markdown
---
name: BPC-157
summary: Synthetic pentadecapeptide derived from a sequence found in gastric juice.
category: Peptides          # Peptides | Blends | Cosmetic | Accessories
cas: 137525-51-0
molecularFormula: C62H98N16O22
molecularWeight: 1419.53 g/mol
sequence: Gly-Glu-Pro-...
vialSize: 5mg
purity: "≥99%"
price: 34                   # GBP, excluding VAT
sku: VP-BPC157-5
inStock: true
featured: true              # shows in the homepage "Frequently ordered" row
order: 10                   # lower numbers sort first
---

Long description goes here.
```

Adding a file creates the product page, adds it to the catalogue and to the sitemap
automatically. Deleting a file removes it everywhere. The fields are validated at build time — a
typo or a missing required field fails the build with a message naming the file, rather than
shipping a broken page.

**Prices are placeholders.** Set real ones before launch.

---

## How ordering works

The site has no checkout. Visitors add products to an **enquiry list**, which is held in their own
browser (`localStorage`), then submit it as a single enquiry with their details.

This is deliberate:

- UK payment processors are frequently unwilling to underwrite research-chemical merchants, and
  finding one is a business decision that should not block the website going live.
- Most customers want the current batch certificate of analysis, a delivered total including VAT,
  or a purchase order raised before committing anyway.

The enquiry list never leaves the visitor's browser until they press send.

### Connecting the forms

Both the enquiry form and the contact form POST to `site.formEndpoint` in `src/config.ts`. It is
empty by default, which makes both forms fall back to opening the visitor's email client with the
message pre-filled. That works everywhere but depends on them having email set up.

For a proper inbox delivery, sign up for [Formspree](https://formspree.io) (or use Netlify Forms if
hosting there) and paste the endpoint URL into `formEndpoint`. No other change is needed — the
form markup already carries the right field names.

### Adding a real checkout later

If a payment processor is secured, the cleanest route is Stripe Payment Links or Shopify's Buy
Button: add a `checkoutUrl` field to the product schema in `src/content.config.ts` and swap the
"Add to enquiry" button for a link. The catalogue, product pages and design all stay as they are.

---

## Deploying

The build output is a plain static `dist/` directory.

**Cloudflare Pages** (recommended — free, fast, UK edge presence):

1. Connect this repository in the Cloudflare dashboard.
2. Build command `npm run build`, output directory `dist`.
3. Add `vippeptides.co.uk` as a custom domain and follow the DNS instructions.

**Netlify:** same settings — build `npm run build`, publish `dist`.

The domain currently resolves to a parked page, so DNS will need repointing at whichever host is
chosen.

---

## Before you go live

The site is complete and deployable, but these are business decisions, not code:

**Legal — get these reviewed.** The four documents under `/legal` (Terms & Conditions, Privacy
Policy, Shipping & Returns, Research Use Disclaimer) are drafted for a UK research-chemical
supplier and cover the right ground, but they are templates. **A UK solicitor should review them
before launch.** Each file carries a comment saying so.

**Register with the ICO.** Any UK business processing personal data — which includes taking
enquiries through a web form — must register with the Information Commissioner's Office. It costs
£52 a year for a small business. The privacy policy already names the ICO as the complaints route.

**Fill in the company details.** Company number, VAT number and registered address in
`src/config.ts`. Displaying a registered company number is a legal requirement on the website of a
limited company.

**GLP-1 analogues are deliberately not in the catalogue.** Semaglutide, tirzepatide and
retatrutide are prescription-only medicines in the UK, and the MHRA has actively pursued suppliers
listing them — including under research-use labelling. They are not seeded here for that reason.
Adding them is one markdown file, but take legal advice on that specific question first rather
than treating it as a normal catalogue addition.

**Check the product data.** CAS numbers, molecular formulae and weights were compiled from public
chemical databases and should be verified against your actual certificates of analysis before
launch. Purity figures must match what your COAs actually say.

**Set real prices.** All prices in the catalogue are placeholders.

---

## Project structure

```
src/
  config.ts              business details, nav, the research-use notice
  content.config.ts      product schema (validated at build time)
  data/products/         one markdown file per product
  layouts/
    Base.astro           html shell, meta tags, fonts, theme bootstrap
    Legal.astro          wrapper for the four legal documents
  components/
    Header.astro         compliance bar, nav, theme toggle, enquiry badge
    Footer.astro         research-use notice, nav, company details
    ProductCard.astro    catalogue card
    SpecTable.astro      product specification table
  scripts/
    enquiry.ts           the enquiry list (localStorage, guarded)
  pages/
    index.astro          home
    products/            catalogue index and [...slug] product pages
    enquiry.astro        enquiry list and submission form
    quality.astro        testing and documentation process
    about.astro, faq.astro, contact.astro, 404.astro
    legal/               terms, privacy, shipping-returns, disclaimer
  styles/global.css      design tokens and base styles
public/                  favicon, robots.txt
```

## Design notes

Colours, type scale and spacing are all CSS custom properties at the top of
`src/styles/global.css`. Light and dark palettes are the same token names redefined, so changing a
brand colour means editing two values, not hunting through components.

Dark mode follows the operating system by default and can be overridden with the header toggle,
which persists in `localStorage`. The compliance bar at the top of every page deliberately keeps
fixed colours in both themes so it never loses contrast.

Everything is server-rendered at build time. The only client-side JavaScript is the theme toggle,
the mobile menu, the catalogue filter and the enquiry list — all of which degrade to a usable site
if scripts fail.
