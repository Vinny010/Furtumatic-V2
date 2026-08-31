# Step 15 — the Wayback index, and a correction

Date: 2026-08-31

A CDX listing of every archived `gsmg.io` path was obtained. Two findings, one of
which corrects a claim I made an hour earlier in this session.

## Reading the index: size separates real pages from noise

```
 1,245  2020  /theseedisplanted                      REAL
 7,253  2020  /choiceisanillusion…iwroteitmyself     REAL
 6,518  2020  /Puzzle                                REAL
 4,592  2023  /89727c59… (SalPhaseIon)               REAL
 2,227  2020  /img/follow_the_white_rabbit.png       REAL (image/png)

11,863  2025  /TheArchitectChoice                    generic shell
12,224  2026  /followthewhiterabbit                  generic shell
12,486  2026  /salphaseion                           generic shell
12,212  2026  /phase1  /phase2  /phase3              generic shell
11,956  2025  /war  /io  /t  /{q}                    generic shell
```

Genuine puzzle pages are **1-8 KB and captured 2019-2023**. Everything in the
**11.5-13 KB** band is the modern GSMG.io single-page app returning HTTP 200 with
the same marketing shell for *any* path — which is why `/t`, `/io`, `/war` and
`/{q}` all appear to "exist".

**Consequence:** the archived `/TheArchitectChoice` (2025, 11,863 bytes) is **not**
the Architect page. Nor is `/followthewhiterabbit` (2026, 12,224 bytes). Both
captures are the generic shell. Note the listing used `collapse=urlkey`, so it shows
one snapshot per URL; earlier captures may exist and are not visible in it.

## CORRECTION — the "fourth blob" has no provenance

Earlier in this session an external analysis referred to a fourth blob with salt
`74c974e3f92e64b5`, which I could not verify and then, on finding it in this index,
reported as "real, and now in hand." **That overstated it.**

The blob is real as a *string*: the URL path
`gsmg.io/53616c7465645f5f74c974e3f92e64b5…` decodes from hex to a well-formed
112-byte OpenSSL object — `Salted__`, salt `74c974e3f92e64b5`, 96 bytes of
ciphertext (so a plaintext of 80-95 bytes). It is stored as `data/urlpath_blob.b64`
and is confirmed **not** a re-encoding of any known blob: every salt and ciphertext
prefix differs from the phase-2, phase-3, phase-3.2, SalPhaseIon and Cosmic Duality
blobs.

But its CDX rows say:

```
/53616c…0607   2026-01-05   text/html 200   12,381 bytes
/53616c…97b5   2026-02-07   text/html 200   12,653 bytes   (a TRUNCATED form)
```

Both are the ~12 KB generic shell. **The site returned its marketing page**, meaning
that URL was never a real page — so the blob in the path is somebody's *input*, not
the site's *output*.

Corroborating, the same index contains plainly visitor-generated paths: lodash
source-code fragments, `/{q}`, `/returns truthy for **all** elements of`, and
base64-looking strings. The Wayback Machine records what crawlers and visitors
*hit*, not what existed. And a truncated version of the same blob was archived a
month after the full one — consistent with a person pasting it in stages.

**Conclusion: the fourth blob is almost certainly a solver's artifact, not author
material.** It was swept anyway — every corpus built in this repo, 4.18M candidates,
plus the 2^26 subset enumeration — and is negative. It should not be treated as one
of the puzzle's open objects without evidence of authorship.

## What the index does offer

1. **`/img/follow_the_white_rabbit.png`**, 2,227 bytes, `image/png`, captured
   2020-11-15 — the same batch as the other genuine puzzle images. Not held here.
   `https://web.archive.org/web/20201115074715if_/https://gsmg.io/img/follow_the_white_rabbit.png`
2. **A 2023 SalPhaseIon capture** (4,592 bytes) to diff against the 2026 one held
   here, in case the page changed.
3. **Un-collapsed CDX queries** on `/TheArchitectChoice` and `/followthewhiterabbit`
   — if any row shows 1-8 KB from 2019-2021, the real page was archived.

## Standing

The 2^42 interval is exhausted (BSGS, 21 seconds, no key). The scalar hypotheses are
structurally excluded. The fourth blob is downgraded to unattributed. What remains
is the same data question, now sharper: **was the Architect Choice page ever
archived at all?** One CDX query answers it.
