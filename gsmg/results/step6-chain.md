# Step 6 — the stage chain, decrypted from live captures

Date: 2026-08-31

## What was captured

Two more pages, saved as MHTML:

- `data/page_theseedisplanted.mhtml` — `gsmg.io/theseedisplanted`
- `data/page_phase2_phase3.mhtml` — the phase 2 / phase 3 page

`tools/chain.py` walks the chain from the second capture, verifying each
password against its published digest before use:

```
phase 2    password sha256 eb3efb5151e62559…  OK    672 -> 648 bytes
phase 3    password sha256 1a57c572caf3cf72…  OK   4112 -> 4090 bytes
phase 3.2  password sha256 250f37726d686293…  OK   2448 -> 2422 bytes
```

All three plaintexts are now held locally rather than quoted second-hand:
`data/phase2_plain.txt`, `data/phase3_plain.txt`, `data/phase32_plain.txt`.

## What the captures added

The `theseedisplanted` page carries an HTML comment the write-ups do not quote —
`<!-- Nice to see you around! Good luck little bunny hunter ;) -->` — and its
hidden form posts to `gsmg.io/phase1verification`. The phase 2/3 page carries
`<!-- You made it to the next step! Good luck little bunny hunter ;) -->`.

One discrepancy worth recording. The FEN printed on the phase 2 page is

```
B5KR/1r5B/6R1/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 w - - 0 1
```

but part 7 of the composite password is

```
B5KR/1r5B/2R5/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 b - - 0 1
```

The page asks "And now a buddhist is forced to move. What will be the next
situation?" — so part 7 is the position *after* the forced move, not the position
printed. The published composite is the answer, not a transcription.

## Phase 3.2 contains three unexploited objects

1. **A 1,539-byte cipher block** over a small symbol set — the Beaufort stage.
2. **A 155-digit decimal string**, undocumented in either write-up.
3. **A further AES blob**, which is the next link in the chain toward the white
   rabbit and Architect Choice pages.

## Sweeps run

Corpus built from the real decrypted stage text — 666 word tokens, all 1-7 word
windows, the page's named phrases, the digit string and its base shifts, and
digests of everything: 25,623 candidates, four password modes, both blob variants.

```
variant A   25,623 candidates   204,984 trials   720 survivors   0 printable
variant B   25,623 candidates   204,984 trials   710 survivors   0 printable
```

Also completed: all 2^23 letter-to-bit masks over the **correct** 256-symbol object
(from the 5×5 Bifid), both blobs, four password modes:

```
variant A   16,777,216 candidates   134,217,728 trials   525,695 survivors   0 printable
variant B   16,777,216 candidates   134,217,728 trials   526,695 survivors   0 printable
```

All negative.

## Still not reached

The **Architect Choice** page. The community bypassed it entirely — their own notes
say the final page was "reached by hashing the text of the first puzzle page rather
than through the Architect Choice" — and the final page's decoded instruction
`lastwordsbeforearchichoice` points at text on that page. The route to it runs
through the remaining phase 3.2 blob, whose password is not yet known.
