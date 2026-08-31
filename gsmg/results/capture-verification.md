# Capture completeness — both textareas verified

Date: 2026-08-31

The concern: the page's two `<textarea>` elements scroll on screen, so a capture
might hold only what was visible. It does not — MHTML saves the DOM source, and a
textarea's full value is in the markup regardless of scroll position. Proven rather
than asserted:

## SalPhaseIon

1075 tokens, matching the documented count. All five published decodings reproduce
from it (`tools/parse_page.py`).

## Cosmic Duality — the conclusive one

1792 base64 characters -> 1344 bytes -> `Salted__`, salt `2d3f6fe06dc950e6`, 1328
bytes of ciphertext = 83 AES blocks. Decrypted with the published XOR-chain key
under EVP_BytesToKey/MD5:

```
plaintext        1327 bytes
sha256           4f7a1e4efe4bf6c5581e32505c019657cb7b030e90232d33f011aca6a5e9c081
published        4f7a1e4efe4bf6c5581e32505c019657cb7b030e90232d33f011aca6a5e9c081
```

AES-CBC chains across all 83 blocks. A single missing base64 character would change
the block count and destroy every block after it. Matching the published digest is
only possible if the capture is byte-complete.

## Full chain reproduced

`tools/dualite_chain.py` runs the whole thing from the capture alone and checks
every step against a published value:

```
XOR-chain key   : a795de11…52e50735                    OK
plaintext       : 1327 bytes, sha256 4f7a1e4e…         OK
secondary       : 103 chars, ords 80..117, 29 distinct
Half            : 1JG648yaB7Wp2dpUfcZoRSD4q35oq47vCu   OK
                  15E3pcDDXSKhvi3CLVhRTHEgd8dbVKvSZg   OK
Better half     : 145ZQ9siLrsXBKf465wjdyQYAP5dRwhRhQ   OK
                  1FhbJnrdq1FmeiXrpTqnpQ8jvYV7naze96   OK
trailing 4 bytes: fc0c1b02
```

All four addresses match. This doubles as certification of the whole toolchain —
AES, EVP_BytesToKey, secp256k1, HASH160, Base58Check — against a chain with known
answers, before any of it is pointed at the unsolved blob.

## One correction to the published account

The community write-up describes the 103-character secondary string as having
"exactly 38 distinct symbols". Its ordinals span 80..117, which is 38 *possible*
values, but only **29** distinct symbols actually occur. The base-38 decode is
unaffected — the digit alphabet is set by the range, not by occupancy — but the
count as stated is wrong.
