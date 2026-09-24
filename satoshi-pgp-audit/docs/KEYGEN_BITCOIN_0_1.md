# How Bitcoin 0.1 generated keys - and why timing replication cannot recover them

Source: the original Satoshi release, mirrored at `trottier/original-bitcoin`
(`src/key.h`, `src/util.cpp`). Quoted verbatim below.

## The key generation call

`src/key.h`:

```cpp
void MakeNewKey() {
    if (!EC_KEY_generate_key(pkey))
        throw key_error("CKey::MakeNewKey() : EC_KEY_generate_key failed");
}
```

The private scalar is drawn by OpenSSL's `EC_KEY_generate_key`, which pulls from
OpenSSL's CSPRNG (`RAND_bytes` internally). Everything of interest is in how that
CSPRNG was seeded.

## The seeding

`src/util.cpp`:

```cpp
RAND_screen();                                  // hash of the entire screen's pixels

QueryPerformanceCounter(&PerformanceCount);     // raw CPU tick counter (not ms)
RAND_add(&PerformanceCount, sizeof(PerformanceCount), 1.5);

// up to 250,000 bytes of the Windows performance registry:
RegQueryValueEx(HKEY_PERFORMANCE_DATA, "Global", NULL, NULL, pdata, &nSize);
SHA256(pdata, nSize, (unsigned char*)&hash);    // every process's CPU/mem/IO/net
RAND_add(&hash, sizeof(hash), min(nSize/500.0, (double)sizeof(hash)));
```

So each private key is 256 bits pulled from a pool seeded by:

- the pixels on the screen at the time (`RAND_screen`),
- the CPU's high-resolution performance counter (`QueryPerformanceCounter`), and
- a ~250 KB snapshot of the whole machine's live performance counters, SHA-256'd in.

The wall clock (`GetTime()`, seconds) appears only as a gate on how often the
expensive perfmon reseed runs (every 5 minutes) - it never feeds the key.

## Why "replicate it to the millisecond" cannot work

1. The millisecond is not the seed. The clock gates reseeding; it is not an input to
   the key. Knowing it yields none of the entropy.
2. `QueryPerformanceCounter` is the raw CPU tick count since boot, not a clock -
   reproducing it needs the exact boot instant and every cycle since, to the tick.
3. The 250 KB perfmon blob is a snapshot of the entire machine's internal state at
   that instant, in 2008/2009. Unrecoverable.
4. `RAND_screen` hashed whatever was on the monitor. Unrecoverable.
5. The CSPRNG state is path-dependent: the state at key N depends on every prior
   draw and reseed in that process's life.

To reconstruct a key you would need the screen contents, the exact CPU tick, and a
250 KB dump of the machine's live counters at that microsecond, on hardware that no
longer exists. This is the "requires unavailable internal generator state" category.

## Context: this is a STRONG generator, not a weak one

The failures that let keys be recovered by timing/enumeration all had a collapsed
seed:

| Generator | Effective seed | Replicable |
|---|---|---|
| naive `srand(time())` | the current second | yes |
| Debian OpenSSL (CVE-2008-0166) | process id (~2^15) | yes |
| Bitcoin 0.1 | screen + CPU counter + 250 KB live system state | no |

Satoshi's seeding was, if anything, over-engineered - hashing a quarter-megabyte of
system telemetry into the pool. That is why every RNG-defect test in this project
(related keys, nonce reuse, keyspace collapse, deterministic chaining) comes back
clean: the generator had strong, machine-specific, high-entropy seeding, and the
machine that held that entropy is gone.
