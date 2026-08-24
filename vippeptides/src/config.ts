/**
 * Central site configuration.
 *
 * Everything a non-developer is likely to need to change lives here:
 * business details, contact routes, and the form endpoint. Nothing else
 * in the codebase hardcodes these values.
 */

export const site = {
  name: 'VIP Peptides',
  domain: 'vippeptides.co.uk',
  url: 'https://vippeptides.co.uk',
  tagline: 'Research-grade peptides, independently tested.',
  description:
    'UK supplier of research-grade peptides. Every batch is supplied with a third-party certificate of analysis. For laboratory research use only.',

  /** Registered trading details — replace with the real ones before launch. */
  company: {
    legalName: 'VIP Peptides Ltd',
    companyNumber: 'TBC',
    vatNumber: 'TBC',
    address: {
      line1: 'TBC',
      city: 'TBC',
      postcode: 'TBC',
      country: 'United Kingdom',
    },
  },

  contact: {
    email: 'hello@vippeptides.co.uk',
    salesEmail: 'orders@vippeptides.co.uk',
    phone: '',
    hours: 'Monday to Friday, 9am – 5pm (UK time)',
  },

  social: {
    instagram: '',
    x: '',
  },

  /**
   * Where the enquiry form POSTs. Static hosting has no backend, so point
   * this at a form service — Formspree (https://formspree.io) or Netlify
   * Forms both work with the existing markup.
   *
   * Leave empty to fall back to a mailto: link, which works everywhere but
   * depends on the visitor having an email client configured.
   */
  formEndpoint: '',

  /** Minimum age required to browse. Set to 0 to disable the age gate. */
  minimumAge: 18,
};

/** Shown site-wide. This is the single most important line on the site. */
export const RESEARCH_USE_NOTICE =
  'All products are supplied strictly for in-vitro laboratory research use only. They are not medicines, not dietary supplements, and are not for human or veterinary consumption, ingestion, injection or any form of in-vivo use.';

export const nav = [
  { label: 'Products', href: '/products' },
  { label: 'Quality', href: '/quality' },
  { label: 'About', href: '/about' },
  { label: 'FAQ', href: '/faq' },
  { label: 'Contact', href: '/contact' },
];

export const legalNav = [
  { label: 'Terms & Conditions', href: '/legal/terms' },
  { label: 'Privacy Policy', href: '/legal/privacy' },
  { label: 'Shipping & Returns', href: '/legal/shipping-returns' },
  { label: 'Research Use Disclaimer', href: '/legal/disclaimer' },
];
