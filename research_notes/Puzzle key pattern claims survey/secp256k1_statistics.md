# Statistical properties of secp256k1 public keys and hash160 addresses, and whether anything correlates with the private key (survey as of September 2026)

**Access note for the report writer.** During this session the network egress proxy blocked almost every primary host: eprint.iacr.org, iacr.org, arxiv.org, link.springer.com, mdpi.com, en.bitcoin.it, safecurves.cr.yp.to, cr.yp.to, elligator.org, crypto.stanford.edu, crypto.stackexchange.com, bitcoin.stackexchange.com (search only), medium.com, imperialviolet.org, blog.cryptographyengineering.com, paulmillr.com, wikipedia.org, semanticscholar.org, coinfabrik.com, keyhunters.ru, lbc.cryptoguru.org, bitcointalksearch.org, news.ycombinator.com, web.archive.org. Only github.com pages were fetchable in full. Every finding below marked "(snippet)" rests on the search engine's summary/snippet of the cited page, not on a full read; findings marked "(fetched)" were read in full. Dates given are publication dates from the citations themselves.

---

## Key question 1: Distribution of x(kG), y(kG) as k varies — uniformity, indistinguishability, known non-uniformities (half of field elements are valid x's, Elligator)

### Takeaway
The literature agrees that (a) the set of valid x-coordinates of a Weierstrass curve is only ~half of the field, so a stream of raw public keys is trivially distinguishable from uniform random 256-bit strings (this is the entire motivation for Elligator, 2013), but (b) within the set of valid points, the map k -> kG is a bijection onto the group, so for uniformly random k the point kG is exactly uniform on the curve; the "half the x's are valid" bias is a property of the curve, not of k, and carries no information about which k produced a given point.

### Cited Findings
- Elligator (Bernstein, Hamburg, Krasnova, Lange, 2013): "elliptic-curve points are easily distinguishable from uniform random strings of bits" and the paper "introduces a new bijection between strings and about half of all curve points; this bijection is applicable to every odd-characteristic elliptic curve with a point of order 2, except for curves of j-invariant 1728." — [ePrint 2013/325](https://eprint.iacr.org/2013/325) (snippet); [elligator.cr.yp.to PDF](https://elligator.cr.yp.to/elligator-20130828.pdf) (snippet).
- The distinguishing test is the ~50% test: "The usual compressed bit string representation of an elliptic curve point is essentially the x-coordinate of the point, and only about half of all possible x-coordinates correspond to valid points (the other half being x-coordinates of points of the quadratic twist)... While this property holds for any valid Curve25519 point, it only holds for a random number in about 50% of the cases. By observing multiple communication attempts, an attacker can be sure that curve points are being sent." — [ImperialViolet, "Implementing Elligator for Curve25519", A. Langley, 25 Dec 2013](https://www.imperialviolet.org/2013/12/25/elligator.html) (snippet); the Legendre symbol of x^3+7 is the test (snippet, same source and [GNUnet LSD0011 HPKE Elligator KEM](https://lsd.gnunet.org/lsd0011/)).
- For secp256k1 specifically: "there are (n-1)/2 valid x coordinates in total, and each x coordinate has two valid y coordinates (y and -y)... the probability to hit a valid x coordinate with a random element in the field is approximately 0.5", so "approximately a 50% chance that a random 32 byte sequence [after a 0x02/0x03 prefix] represents a valid point on the curve" — search snippet attributed to [Bitcoin Wiki: Secp256k1](https://en.bitcoin.it/wiki/Secp256k1) / related Q&A (snippet; page blocked).
- secp256k1 is a prime-order curve with j-invariant 0 and no point of order 2, so Elligator 1/2 (which need a point of order 2) do not apply; the prime-order case is addressed by Elligator Squared (Tibouchi, 2014), "an algorithm for representing around half of the points on a large class of elliptic curves as close to uniform random strings" — [ePrint 2014/043, "Elligator Squared: Uniform Points on Elliptic Curves of Prime Order as Uniform Random Strings"](https://eprint.iacr.org/2014/043) (snippet). (The inapplicability of Elligator 1/2 to secp256k1 follows from the order-2 requirement stated in the Elligator abstract; I could not fetch text that says "secp256k1" explicitly.)
- Character-sum / equidistribution theory: Shparlinski and coauthors bound "bilinear sums over points of elliptic curves over finite fields" and use them to prove "uniformity of distribution of congruential generators over elliptic curves" — [Springer, "On the Uniformity of Distribution of Congruential Generators over Elliptic Curves"](https://link.springer.com/chapter/10.1007/978-1-4471-0673-9_19) (snippet); [Shparlinski, "Exponential sums over points of elliptic curves", J. Number Theory 2014](https://www.sciencedirect.com/science/article/pii/S0022314X14000547) (snippet). These results are the formal statement that coordinates of multiples kG are equidistributed (up to Weil-bound error terms of order sqrt(p)) as k ranges over intervals.
- A Springer paper (Indocrypt 2007 volume) "A Result on the Distribution of Quadratic Residues with Applications to Elliptic Curve Cryptography" addresses exactly the QR-half structure of x-coordinates — [Springer 978-3-540-77026-8_5](https://link.springer.com/chapter/10.1007/978-3-540-77026-8_5) (snippet; abstract not retrievable).
- SafeCurves has an explicit "ind" (indistinguishability from uniform random strings) criterion and secp256k1 fails it (it also fails "ladder", "complete"; rigidity is "somewhat rigid") — [SafeCurves](https://safecurves.cr.yp.to/) (snippet; blocked). The 2024 successor paper: Bernstein & Lange, "Safe curves for elliptic-curve cryptography", ePrint 2024/1265, 68 pp., published in LNCS 15600 (2025), "surveys interactions between choices of elliptic curves and the security of elliptic-curve cryptography" — [ePrint 2024/1265](https://eprint.iacr.org/2024/1265); [PDF](https://cr.yp.to/papers/safecurves-20240809.pdf) (snippet only).

### Inferences
- "Distinguishable from random" (Elligator's concern) is a metadata/censorship-resistance problem, not a key-recovery problem: the distinguisher only tells you a string *is* a curve point, which is already public knowledge for a Bitcoin public key.
- Since k -> kG is a bijection from Z_n onto the group of order n, the distribution of kG for uniform k in [1, n-1] is exactly uniform on the non-identity points; therefore any statistic of (x, y) has, for random k, exactly the same distribution regardless of any property of k. The only way a statistic of the point could correlate with k is if k itself is non-uniform (e.g. small, structured), which is the situation the "special subsets" attacks (Q4) exploit.
- The Hasse bound and character-sum results mean the x-coordinates of valid points are equidistributed over the field to within ~sqrt(p)/p ≈ 2^-128 relative error; no observable bias exists at any feasible sample size.

### Gaps
- Could not read the full Elligator or SafeCurves text to quote the precise "ind" criterion wording or confirm SafeCurves' per-criterion table for secp256k1 (blocked hosts).
- Did not find any paper claiming a non-trivial (beyond the QR-half) statistical bias in secp256k1 coordinates; absence of evidence, not a proof of absence.

---

## Key question 2: Is there statistical dependence between bits of k and bits of x(kG), y(kG), hash160? What do hardness assumptions imply?

### Takeaway
The formal literature goes further than "no dependence is known": for EC Diffie-Hellman and EC one-way functions there are *bit-security* theorems showing that predicting even a single bit of the coordinates (or of the input) with non-negligible advantage would let you solve the whole problem. Under DDH on secp256k1 and random-oracle modelling of SHA-256/RIPEMD-160, addresses are computationally indistinguishable from uniform 160-bit strings independent of k.

### Cited Findings
- Boneh & Shparlinski, "On the Unpredictability of Bits of the Elliptic Curve Diffie-Hellman Scheme", CRYPTO 2001: "if there is an efficient algorithm for predicting the LSB of the x or y coordinate of abG given (E,G,aG,bG) for a certain family of elliptic curves, then there is an algorithm for computing the Diffie-Hellman function on all curves in this family"; "just predicting one bit of the Elliptic Curve Diffie-Hellman secret in a family of curves is as hard as computing the entire secret." — [Springer 3-540-44647-8_12](https://link.springer.com/chapter/10.1007/3-540-44647-8_12) (snippet); [Boneh abstract page](http://crypto.stanford.edu/~dabo/abstracts/ecdhbits.html) (snippet).
- Jetchev & Venkatesan, "Bits Security of the Elliptic Curve Diffie-Hellman Secret Keys", CRYPTO 2008 — extends the above beyond the LSB "using list decoding techniques" so that "any bit, not just the LSB, is hard" — [ACM DL](https://dl.acm.org/doi/10.1007/978-3-540-85174-5_5) (snippet).
- Duc & Jetchev, "Hardness of Computing Individual Bits for One-way Functions on Elliptic Curves", CRYPTO 2012 (LNCS 7417 pp. 832-849): "if one can predict any of the bits of the input to an elliptic curve based one-way function over a finite field, then we can invert the function." — [ePrint 2011/329](https://eprint.iacr.org/2011/329.pdf) (snippet).
- Shani, "On the Bit Security of Elliptic Curve Diffie-Hellman", PKC 2017 — further bit-security results for ECDH — [Springer 978-3-662-54365-8_15](https://link.springer.com/chapter/10.1007/978-3-662-54365-8_15) (snippet; abstract not retrievable).
- Takhanov et al., "Intractability of Learning the Discrete Logarithm with Gradient-Based Methods", ACML 2023 (PMLR v222 pp. 1321-1336): proves "the concentration of the gradient of the loss function around a fixed point, independent of the logarithm's base," giving "a restricted ability to learn the parity bit efficiently using gradient-based methods, irrespective of the complexity of the network architecture," with experiments "demonstrating the decreasing success rate in predicting the parity bit as the group order increases." — [arXiv 2310.01611](https://arxiv.org/abs/2310.01611); [PMLR](https://proceedings.mlr.press/v222/takhanov24a.html) (snippet).
- Companion result: "Gradient Descent Fails to Learn High-frequency Functions and Modular Arithmetic" — [arXiv 2310.12660](https://arxiv.org/pdf/2310.12660) (snippet, title only).
- Learning-theoretic background: "a class of decryption functions of secure public-key cryptosystems is not PAC-learnable" — search summary citing standard results (snippet; no primary page fetched).

### Inferences
- Bit-security theorems are the strongest form of "no correlation": a statistically detectable dependence between any coordinate bit and k (for random k) would contradict ECDLP/ECDH hardness on secp256k1, which is the same assumption Bitcoin's security already rests on. (Caveat: Boneh-Shparlinski's reduction is over a *family* of isomorphic/twisted curves rather than a single fixed curve; this is a standard technicality and does not weaken the practical conclusion.)
- hash160 adds a second layer: even if some coordinate bit were biased, SHA-256 then RIPEMD-160 (modelled as random oracles) would map the point to a 160-bit string whose bits are independent of everything about the input except its identity. Any correlation between hash160 bits and k would be a distinguisher for SHA-256/RIPEMD-160 composition, i.e. a break of the hash, not of the curve.

### Gaps
- Could not retrieve the exact theorem statements (family definition, advantage bounds) for Boneh-Shparlinski / Jetchev-Venkatesan / Shani because Springer, IACR and Stanford hosts were blocked.
- No source was found that states the bit-security result specifically instantiated for secp256k1; the results are generic over prime-field curves.

---

## Key question 3: Do consecutive or related keys (k, k+1, 2k, k+c) give related points/addresses in any exploitable way beyond the group law?

### Takeaway
Related private keys give related *points* exactly and only via the group law ((k+c)G = kG + cG, (2k)G = 2(kG), and on secp256k1 also (lambda*k)G = (beta*x, y)); these are public linear relations that are exploited by wallet-derivation attacks (BIP32 unhardened) and by Pollard-rho/kangaroo symmetry folding, but they vanish after hash160, and no source reports any address-level relation between related keys.

### Cited Findings
- Endomorphism relation on secp256k1: "On a j = 0 curve the endomorphism (x, y) -> (beta x, y) is multiplication by a cube root of unity lambda mod n, so the walk can be folded by all six automorphisms for sqrt(6): the representative is the smallest of {x, beta x, beta^2 x} (one field multiplication, since beta^2 x = -(x + beta x)) followed by the negation map." — [aburan28/crypto PR #483 (fetched, 2025-26)](https://github.com/aburan28/crypto/pull/483). The PR measured, on a 36-bit j=0 toy curve, "Fold 1 vs Fold 6: 2.69x ratio (theoretical sqrt(6) = 2.45x)", with mean steps "1.11x the theoretical sqrt(pi n/(2 fold)) boundary" (fetched).
- SEC 2 selection of Koblitz parameters: "the recommended parameters associated with a Koblitz curve have been selected by repeatedly selecting parameters that admit an effectively calculable endomorphism until a first order curve has been found" — quoted in [scispace copy of "A comparison between the secp256r1 and the koblitz secp256k1 bitcoin curves" (IJEECS, 2019)](https://scispace.com/pdf/a-comparison-between-the-secp256r1-and-the-koblitz-secp256k1-8b6l4w4qud.pdf) (snippet).
- Linear key relations are exploitable only when the relation itself is secret-linked: Bitcoin Core PR #25366 notes that "Descriptor wallets (by default) use unhardened derivation, so leaking one derived private key is sufficient for an attacker to compute every private key" — [bitcoin/bitcoin PR 25366](https://github.com/bitcoin/bitcoin/pull/25366) (snippet). This is the BIP32 "k_child = k_parent + tweak" relation, i.e. exactly the (k + c) case, exploitable because c is derivable from the public xpub.
- BTC32 puzzle creator on how the puzzle keys relate to each other: "There is no pattern. It is just consecutive keys from a deterministic wallet (masked with leading 000...0001 to set difficulty)." — quoted in [HomelessPhD/BTC32 README (fetched)](https://github.com/HomelessPhD/BTC32/blob/main/README.md); originating Bitcointalk thread topic 1306983 referenced via [Hacker News item 41547443](https://news.ycombinator.com/item?id=41547443) (snippet).
- Analysis of the solved puzzle keys (HomelessPhD, fetched): normalised each key to alpha = (PK_n - 2^(n-1))/2^(n-1) in [0,1], built histograms with several bin widths and computed autocorrelation; found keys "more probable to be found at {0.3-0.5} and {0.6-0.8}" with a cluster at {0.82-0.83}, but concluded there is "no any linear tendency or relation in data" and that the autocorrelation is "mere noise", warning that "a model you are using for prognosis should have a number of parameters less than observations." — [BTC32 README](https://github.com/HomelessPhD/BTC32/blob/main/README.md) (fetched).

### Inferences
- Because the puzzle keys are *masked* outputs of a deterministic wallet (top bits forced to zero, low bits from the wallet's own key stream), the "consecutive" relation is a relation between wallet indices, not an additive relation between the published private keys; the published keys' low bits are, for all practical purposes, independent samples from the wallet's PRNG/hash chain. No relation of the (k, k+1) or (k, 2k) type therefore exists between the puzzle keys, and the creator's statement is consistent with the HomelessPhD "noise" finding.
- Any relation between P1 = kG and P2 = (k+c)G is fully captured by P2 - P1 = cG; this is a public-key operation and yields nothing about k unless c is known *and* one of the two keys is known. After hash160 the relation is destroyed (a random-oracle hash of P2 is independent of the hash of P1), so no address-level relation can exist.
- The 60-70 apparent histogram bumps in the BTC32 analysis are consistent with sampling noise over ~70 points; the author's own overfitting warning is the correct reading.

### Gaps
- I found no academic paper analysing "related-key" leakage for ECDLP in the sense asked (k vs k+1) beyond the group-law identities; the topic appears not to exist as a research question because the identities are trivial.
- Could not fetch the original Bitcointalk 1306983 thread to quote the creator's message directly (host blocked); the quotation is as reproduced in the BTC32 README.

---

## Key question 4: Randomness-test results (NIST STS, Dieharder, TestU01) on EC coordinates or Bitcoin addresses

### Takeaway
No peer-reviewed study was found that runs NIST SP 800-22, Dieharder or TestU01 on streams of secp256k1 coordinates or Bitcoin addresses; the closest items are (a) the NIST/Dieharder suites themselves, (b) a hobbyist neural-network "distinguisher" (demining GitHub) that only rediscovers the known half-of-x structure, and (c) hobbyist pattern-scanners for hash160 that look for repeated bytes.

### Cited Findings
- NIST SP 800-22 Rev.1a defines 15 tests for "binary sequences produced by either hardware or software based cryptographic random or pseudorandom number generators" with alpha = 0.01 — [NIST CSRC SP 800-22r1](https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final) (snippet). Dieharder "includes the 18 original Diehard tests along with additional tests, including some from the NIST suite" — [arXiv 2402.02240, "Recommendations on Statistical Randomness Test Batteries for Cryptographic Purposes"](https://arxiv.org/pdf/2402.02240) (snippet).
- Hobbyist ML distinguisher (demining, GitHub; fetched): dataset of "60,000 samples mixing curve points and random data in a 1:8 ratio", bidirectional GRU with two 1024-unit layers, "approximately 87.83% validation accuracy" after two epochs; the repository "does not claim actual private key recovery" but frames the result as "most serious vulnerability". Reviewer notes from the fetch: "The 1:8 imbalanced dataset may artificially inflate distinguishability"; "No peer review or external validation." — [demining/An-attempt-to-predict-the-behavior-of-the-properties-of-the-secp256k1-Elliptic-Curve](https://github.com/demining/An-attempt-to-predict-the-behavior-of-the-properties-of-the-secp256k1-Elliptic-Curve) (fetched).
- Hobbyist hash160 scanners: "Bitcoin-Address-Analyzer" flags addresses with "very few unique bytes, repeated single bytes, small byte ranges, leading zero bytes, and unusual bit counts" — [ethicbrudhack/-Bitcoin-Address-Analyzer](https://github.com/ethicbrudhack/-Bitcoin-Address-Analyzer) (snippet). A Medium post ("Looking at RIPEMD-160 Bitcoin Addresses for Fun and No Profit", K. Finlow-Bates) computes that for a truly random RIPEMD-160 hex string "the chance of a given digit being followed by nine more is 1/(16^9)" and finds addresses consistent with randomness — [Medium](https://medium.com/@keir_85660/looking-at-ripemd-160-bitcoin-addresses-for-fun-and-no-profit-15f311521fce) (snippet; blocked).
- The search summary explicitly concluded: "I did not find published peer-reviewed studies that specifically apply the complete NIST SP 800-22 test suite to large datasets of Bitcoin hash160 addresses" (search-engine synthesis over the results listed above).

### Inferences
- An 87.8% accuracy on a 1:8 class mix where the majority class is "random 256-bit string" is essentially explained by the known Legendre-symbol structure (a random x is a valid secp256k1 x with probability ~1/2, so ~half of the "random" class is trivially separable if the model learns anything like a QR test, and the base rate of the majority class alone is 88.9%). The result therefore does not demonstrate any structure beyond what Elligator already documents, and says nothing about k.
- A NIST/Dieharder run on raw compressed public keys *would* fail (the first byte is always 0x02/0x03 and x's are QR-filtered); a run on hash160 outputs of random keys would pass by the random-oracle assumption. Neither outcome would bear on key recovery. This is inference; I found no published run to cite either way.

### Gaps
- No published NIST STS / Dieharder / TestU01 results on secp256k1 coordinates or on hash160 streams were found; this is a genuine gap in the literature, most likely because the outcome is theoretically determined and considered uninteresting.

---

## Key question 5: Documented "bias" or "leak" in hash160 / SHA-256 / RIPEMD-160 relevant to key recovery

### Takeaway
There is no documented bias in SHA-256 or RIPEMD-160 outputs usable for preimage or key recovery; the best published cryptanalysis reaches collision attacks on 40 of RIPEMD-160's 80 steps (2023) and no full-round preimage attacks, while the real, well-documented "weakness" of hash160 is structural: it compresses 256-bit keys to 160 bits, so ~2^96 private keys share each address and generic preimage cost is 2^160, which is still far beyond 2^128 ECDLP cost.

### Cited Findings
- "New Records in Collision Attacks on RIPEMD-160 and SHA-256" (Li, Liu, Wang, EUROCRYPT 2023): collision attacks "on RIPEMD-160 can be improved to 40 steps" (out of 80); earlier best was 34 steps — [ePrint 2023/285](https://eprint.iacr.org/2023/285) (snippet). SHA-256 collision records in the same paper are on reduced rounds only (snippet does not give the count).
- Summary table of "known and new preimage and collision attacks on RIPEMD-160" exists in the 2013-14 literature (ResearchGate table) — [ResearchGate](https://www.researchgate.net/figure/Summary-of-known-and-new-preimage-and-collision-attacks-on-RIPEMD-160-hash-and_tbl1_261294807) (snippet; no full-round preimage attack listed).
- Quantum bound: "Grover's algorithm against the Bitcoin address hash HASH160 cuts preimage security from 160 to about 80 bits (though still Grover-bounded and reachable only if an address is reused)" — [arXiv 2606.14484, "Quantum Horizon: An evaluation of quantum computing as a threat to Bitcoin and Ethereum" (2026)](https://arxiv.org/pdf/2606.14484) (snippet).
- Collision-search framing from the Large Bitcoin Collider theory page: "the effective search space until any collision is found is approximately 159 bits minus log2(number of addresses in use)" — [LBC theory](https://lbc.cryptoguru.org/man/theory) (snippet; blocked).
- Design rationale: "Using two different algorithms reduces dependency on a single hash function" — [ADHDecode RIPEMD-160 page](https://adhdecode.com/cryptography/hash-functions/ripemd-160/) (snippet); Buchanan, "Why Two Hashes? Why RIPEMD160 and SHA-256?" — [Medium/ASecuritySite](https://medium.com/asecuritysite-when-bob-met-alice/ripemd160-f28062242045) (snippet).
- Weak-key (not weak-hash) recovery: "In 2020 Sala, Sogiorno and Taufer were able to find the private keys of some Bitcoin addresses... This result was unexpected"; Di Scala et al. (2022) "widen this analysis by mounting a similar attack to other small subsets of the set of private keys" on Ethereum, Dogecoin, Litecoin, Dash, Zcash, Bitcoin Cash via "exhaustive search for all the addresses that have ever appeared in these blockchains", and consider Curve25519 and P-256 — [arXiv 2206.14107 / Mathematics 10(15):2746, 2022](https://arxiv.org/abs/2206.14107); [MDPI](https://www.mdpi.com/2227-7390/10/15/2746) (snippet). The 2020 work is "A Small Subgroup Attack on Bitcoin Address Generation", Mathematics 8(10):1645 — [MDPI](https://mdpi.com/2227-7390/8/10/1645/htm) (snippet, title only).
- Puzzle-specific: the Bitcoin puzzle "serves as a crude measuring instrument of the cracking strength of the community" and its keys are "masked with leading zeros to set difficulty" — [BTC32 README (fetched)](https://github.com/HomelessPhD/BTC32/blob/main/README.md); the pattern of "decreasing numbers of zeroes" noticed by Bitcointalk users "relates to the technical structure of the puzzle rather than a cryptographic weakness" — [Hexn, "Cracking Bitcoin Puzzles"](https://hexn.io/blog/what-are-bitcoin-puzzles-xdz8m8nn15lx5xci93jih6bs) (snippet).

### Inferences
- The Sala/Sogiorno/Taufer and Di Scala results are the only academic "key recovery from addresses" successes found, and they work by *enumerating small structured subsets of k* (e.g. small integers, small subgroups) and hashing forward to compare with the address set; they exploit bad key generation, not any leak in hash160 or the curve. They are therefore evidence *for* the one-way model: the only way found to invert address -> key is to guess k from a tiny candidate set.
- Because ~2^96 keys map to each hash160, an attacker who only sees an address has strictly less information about k than one who sees the public key; hash160 can only add uncertainty, never leak.
- Reduced-round collision results (40/80 steps) have no bearing on preimage resistance of the full function and none on key recovery.

### Gaps
- Could not read the full Di Scala et al. paper or Sala et al. 2020 to report the exact subsets searched and the number of funded addresses found (MDPI/arXiv blocked).
- Did not find any paper claiming an output bias in full-round RIPEMD-160 or SHA-256; the reduced-round collision literature is the entire relevant record.

---

## Key question 6: Machine-learning attempts to predict private keys from public keys or addresses

### Takeaway
Published ML work reaches the negative conclusion: gradient-based learning cannot even learn the parity bit of a discrete log (Takhanov 2023, ACML), success rates fall toward chance as the group grows, and hobbyist "RNN address-to-key" projects report no recoveries; the one positive-sounding hobbyist result (87.8% distinguishing points from random strings) rediscovers the public half-of-x structure and does not touch k.

### Cited Findings
- Takhanov et al., ACML 2023 (PMLR v222): gradient concentration "around a fixed point, independent of the logarithm's base," hence "restricted ability to learn the parity bit... irrespective of the complexity of the network architecture," verified empirically with "decreasing success rate in predicting the parity bit as the group order increases" — [arXiv 2310.01611](https://arxiv.org/abs/2310.01611); [PMLR](https://proceedings.mlr.press/v222/takhanov24a.html) (snippet).
- "Gradient Descent Fails to Learn High-frequency Functions and Modular Arithmetic" — [arXiv 2310.12660](https://arxiv.org/pdf/2310.12660) (snippet; title only).
- "Neural Network in Elliptic Curve Cryptography" (Springer, 2025) — "assessments of artificial neural network effectiveness on elliptic curve-related problems" — [Springer 978-3-031-58641-5_21](https://link.springer.com/chapter/10.1007/978-3-031-58641-5_21) (snippet; no results retrievable).
- Bitcointalk thread "Neural Networks and Secp256k1" (topic 5337128): OP posted RNN code "designed to convert training Bitcoin addresses to private keys", intended "to get ballpark private-key estimates for use with other tools"; the search synthesis reports no practical breakthrough — [bitcointalksearch mirror](https://bitcointalksearch.org/topic/neural-networks-and-secp256k1-5337128/all.html) (snippet; blocked).
- demining GitHub distinguisher (see Q4): 87.83% accuracy classifying curve points vs random strings at a 1:8 ratio; "does not claim actual private key recovery" — [GitHub (fetched)](https://github.com/demining/An-attempt-to-predict-the-behavior-of-the-properties-of-the-secp256k1-Elliptic-Curve).
- Non-attack ML use of secp256k1: "Towards ECDSA key derivation from deep embeddings for novel Blockchain applications" (2017) derives keys *from* embeddings, not the reverse — [arXiv 1711.04069](https://arxiv.org/pdf/1711.04069) (snippet; title/abstract only).
- Related classical-algorithm claims that are explicitly non-threatening: "A Guess and Determine Attack on the ECDLP" (arXiv 2607.09814, Aug 2026): "the authors note that this attack poses no security risk to elliptic curve cryptography at this time"; "A new method for solving the ECDLP" (arXiv 2005.05039, 2021) solved groups "of order up to 2^50" — [arXiv 2607.09814](https://arxiv.org/abs/2607.09814); [arXiv 2005.05039](https://arxiv.org/abs/2005.05039) (snippets).

### Inferences
- The Takhanov result is the theoretical explanation for every failed hobbyist attempt: the parity bit of log_g(h) is an approximately orthogonal family of functions across bases, so the gradient signal is exponentially small in the group size and no architecture change fixes it.
- Bit-security theorems (Q2) imply that any ML model that predicted a single coordinate bit of kG (or bit of k from kG) with non-negligible advantage would already be a full ECDLP/ECDH solver; no such model is claimed anywhere in the retrieved literature.

### Gaps
- Could not fetch the demining repository's training data or verify its accuracy claim independently; the number is self-reported.
- No peer-reviewed paper attempting address -> private key ML prediction was found; the topic exists only in forum/GitHub form.

---

## Key question 7: Known weaknesses specific to secp256k1's parameters (Koblitz, j-invariant 0, endomorphism) and their practical effect

### Takeaway
The only quantified consequence of secp256k1's special structure is a constant-factor sqrt(6) Pollard-rho speedup from its 6-element automorphism group (versus sqrt(2) for a generic curve), leaving ~2^127.8 expected group operations; SafeCurves, the Bernstein-Lange 2024 survey, and the Bitcoin-oriented comparisons all state that no attack exploiting j = 0 beyond this is known, and the curve's non-random construction is usually cited as a rigidity *advantage* rather than a weakness.

### Cited Findings
- Structure: "secp256k1 has j-invariant 0... and therefore has a very special structure and calculable endomorphism that can be used to accelerate implementations through GLV decomposition" — [IJEECS comparison paper via scispace](https://scispace.com/pdf/a-comparison-between-the-secp256r1-and-the-koblitz-secp256k1-8b6l4w4qud.pdf) (snippet). (Note: that paper's phrase "super-singular" is a misuse; a j=0 curve over F_p with p ≡ 1 mod 3 is ordinary. This correction is my inference from standard theory and is not sourced.)
- Rho speedup: "Pollard rho can be adapted to take advantage of the endomorphism using two-dimensional random walks, resulting in an attack about a factor of 2 faster (roughly 2^127 operations instead of 2^128), but this constant-factor speedup does not change the exponential nature of the problem" — search synthesis over [SafeCurves](https://safecurves.cr.yp.to/) and the comparison paper (snippet). The sqrt(6) folding and its measured 2.69x (theory 2.45x) on a toy curve — [aburan28/crypto PR #483 (fetched)](https://github.com/aburan28/crypto/pull/483). "All known constant-factor improvements (negation, endomorphisms, parallelism) still leave secp256k1 firmly out of reach, maintaining its ~128-bit security strength" with 2^127.8 as the commonly cited figure — search synthesis (snippet, no single primary page fetched).
- SafeCurves position: "while secp256k1's extra structure might in theory open the door to more exotic attacks, none are known, and the curve is still considered safe barring a breakthrough"; its listed failures are "implementation-related (laddering and completeness issues, which are side-channel concerns, not mathematical breaks)" — [SafeCurves](https://safecurves.cr.yp.to/) (snippet; blocked). 2024 survey: Bernstein & Lange, ePrint 2024/1265 (snippet; blocked).
- Rigidity argument: "secp256k1 was chosen over the random secp256r1 in order to avoid having to trust the 'randomness' used to generate the curves parameters, and to avoid the possibility of a backdoor"; "The simplicity of its parameters (a = 0, b = 7) means there is no suspicion of hidden backdoors" — search synthesis citing [Bitcoin Wiki Secp256k1](https://en.bitcoin.it/wiki/Secp256k1) and [Elementary Bitcoin ch. 5](https://elementarybitcoin.org/chapters/05-secp256k1.html) (snippets; blocked). Counter-view also present: "Some cryptographers are skeptical about the secp256k1 curve due to its poorly explained curve parameter derivation process" — [IJEECS comparison paper](https://scispace.com/pdf/a-comparison-between-the-secp256r1-and-the-koblitz-secp256k1-8b6l4w4qud.pdf) (snippet).
- Koblitz & Menezes, "A Riddle Wrapped in an Enigma" (ePrint 2015/1018): historical discussion of NSA Suite B and ECC; background that "new sub-exponential attacks that worked in [RSA/DH] settings did not seem to have any analogue in the ECC world" — [ePrint 2015/1018](https://eprint.iacr.org/2015/1018.pdf) (snippet); commentary by M. Green, 22 Oct 2015 — [blog.cryptographyengineering.com](https://blog.cryptographyengineering.com/2015/10/22/a-riddle-wrapped-in-curve/) (snippet; blocked).
- ECIES-specific review: H. Mayer, "Some Comments on the Security of ECIES with secp256k1" (CoinFabrik, 2016) — [PDF](https://www.coinfabrik.com/wp-content/uploads/2016/06/some_comments_on_the_security_of_ecies_with_secp256k1.pdf) (blocked; listed in search only).
- "Diving into Alternate Elliptic Curves for Bitcoin: A Security Analysis", NISS 2024 — [ACM DL](https://dl.acm.org/doi/10.1145/3659677.3659714) (snippet; title only).

### Inferences
- The endomorphism gives the attacker exactly the same thing it gives the defender: a 6-fold symmetry of the group. Folding rho by it is the *entire* known exploitation of j = 0; it reduces work from ~2^128 to ~2^127.8 (sqrt(6) vs sqrt(2) relative to plain rho), which is irrelevant in practice.
- None of the retrieved sources connect the endomorphism to any statistical property of coordinates that depends on k. The symmetry (x,y) -> (beta x, y) maps kG to (lambda k)G, which is a relation between *different* keys, not a leak about a given key.

### Gaps
- Could not read SafeCurves' current per-criterion table for secp256k1 or the 2024 Bernstein-Lange survey text; specific numbers (rho cost, CM discriminant) are from memory of the site and are omitted rather than risk misquoting.
- The CoinFabrik/Mayer note and the NISS 2024 paper could not be read.

---

## Overall synthesis for the report writer

- The literature contains exactly one documented statistical non-uniformity in secp256k1 public keys — that only ~half of field elements are valid x-coordinates (Legendre symbol of x^3+7) — and it is a property of the curve, known since at least the Elligator paper (2013), and independent of k.
- Formal bit-security results (Boneh-Shparlinski 2001; Jetchev-Venkatesan 2008; Duc-Jetchev 2012; Shani 2017) show that predicting even one bit of EC coordinates/inputs with non-negligible advantage is equivalent to solving ECDH/ECDLP; the ML-theory result of Takhanov et al. (2023) shows gradient methods cannot learn even the parity bit of a discrete log.
- Related keys give related points only through the group law and the lambda/beta endomorphism, which are public and already fully accounted for in Pollard rho/kangaroo (sqrt(6) folding); hash160 erases these relations.
- No NIST/Dieharder/TestU01 study of coordinates or addresses was found; hobbyist "distinguisher" results (87.8% on a 1:8 mix) are explained by the known half-of-x structure.
- The only academic address-to-key recoveries (Sala-Sogiorno-Taufer 2020; Di Scala et al. 2022) enumerate tiny structured key subsets and hash forward; they exploit bad key generation, not any leak in the curve or hash160.
- The Bitcoin puzzle creator's own statement is that keys are consecutive deterministic-wallet keys masked with leading zeros; the one quantitative pattern analysis found (HomelessPhD/BTC32) concludes the observed clustering is noise and warns against overfitting.
