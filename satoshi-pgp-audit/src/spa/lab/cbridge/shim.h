/* Minimal environment for compiling GnuPG 1.4.7 pool code standalone.
 *
 * Provides only what cipher/rmd160.c :: transform() and cipher/random.c ::
 * mix_pool() actually reference. Nothing here alters the extracted code's
 * behaviour; it replaces GnuPG's build system, not its logic. */
#ifndef SPA_SHIM_H
#define SPA_SHIM_H

#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

typedef unsigned char byte;
typedef uint32_t u32;
typedef unsigned long ulong;

/* cipher/bithelp.h */
static inline u32 rol(u32 x, int n) { return (x << n) | (x >> (32 - n)); }

/* cipher/rmd.h - verbatim struct layout */
typedef struct {
    u32  h0,h1,h2,h3,h4;
    u32  nblocks;
    byte buf[64];
    int  count;
} RMD160_CONTEXT;

/* cipher/random.c pool geometry */
#define BLOCKLEN  64
#define DIGESTLEN 20
#define POOLBLOCKS 30
#define POOLSIZE (POOLBLOCKS*DIGESTLEN)

/* random.c calls burn_stack() purely to scrub the stack; it has no effect on
 * the mixed output, so a no-op preserves behaviour exactly. */
static void burn_stack(int bytes) { (void)bytes; }

#endif /* SPA_SHIM_H */
