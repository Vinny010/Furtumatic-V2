"""satoshi-pgp-audit: reproducible audit of the historical GnuPG 1.4.7 environment
that public sources associate with OpenPGP key 0x5EC948A1 (Satoshi Nakamoto, 2008-10-30).

The package is deliberately split so that *observation* and *speculation* never share a
code path:

  spa.openpgp   - pure RFC 4880 parsing. No cryptographic judgement, no interpretation.
  spa.analysis  - measurements over parsed material. States what IS observable.
  spa.lab       - synthetic experiments. Never touches real private material (there is none).
  spa.report    - assigns each finding to exactly one of five evidentiary categories.
"""

__version__ = "1.0.0"
