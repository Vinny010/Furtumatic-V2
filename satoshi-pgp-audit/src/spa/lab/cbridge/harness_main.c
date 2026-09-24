/* Differential-test harness.
 *
 * Reads POOLSIZE bytes of pool state on stdin, applies the extracted historical
 * mix_pool() ROUNDS times, writes the resulting POOLSIZE bytes to stdout.
 * Deterministic: no entropy gathering, no clock, no OS randomness. */

int main(int argc, char **argv)
{
    /* The C allocation is POOLSIZE+BLOCKLEN: the tail is mix_pool's hashbuf. */
    static byte pool[POOLSIZE + BLOCKLEN];
    long rounds = 1, i;
    size_t got = 0, n;

    if (argc > 1) rounds = atol(argv[1]);

    while (got < POOLSIZE) {
        n = fread(pool + got, 1, POOLSIZE - got, stdin);
        if (n == 0) { fprintf(stderr, "short pool input\n"); return 2; }
        got += n;
    }
    for (i = 0; i < rounds; i++)
        mix_pool(pool);

    if (fwrite(pool, 1, POOLSIZE, stdout) != POOLSIZE) return 3;
    return 0;
}
