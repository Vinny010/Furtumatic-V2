"""Bridge to the genuine GnuPG C implementation.

Extracts mix_pool() and the RIPEMD-160 compression function from a pinned upstream
source tree, compiles them, and exposes them for differential testing against the
Python model.
"""
