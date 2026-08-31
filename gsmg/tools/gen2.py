"""Step-2 corpus: candidates built from the live final page, not documentation prose."""
import itertools, hashlib, sys
s=open('salphaseion_stream.txt').read()
seen=set(); out=sys.stdout
def emit(x):
    for v in (x, x.lower(), x[::-1], x.lower()[::-1]):
        if 0<len(v)<=400 and v not in seen:
            seen.add(v); out.write(v+"\n")

PREFIX  = s[0:91]
SEG570  = s[195:765]
MIX     = s[765:895]
BLOBREG = s[895:1075]
p1="U2FsdGVkX186tYU0hVJBXXUnBUO7C0+X4KUWnWkCvoZSxbRD3wNsGWVHefvdrd9z"
p2="QvX0t8v3jPB4okpspxebRi6sE1BMl5HI8Rku+KejUqTvdWOX6nQjSpepXwGuN/jJs"

# page-verbatim objects
for r in (PREFIX,SEG570,MIX,BLOBREG,p1,p2,s): emit(r)

TOK=["matrixsumlist","enter","lastwordsbeforearchichoice","thispassword",
     "yourlastcommand","secondanswer","ourfirsthintisyourlastcommand","shabef","sha256",
     "anstoo","shabefanstoo","btcseed","BTCSEED","salphaseion","cosmicduality","dualite",
     "theseedisplanted","causality","esrever","archichoice","thearchitect","architect",
     "half","betterhalf","whiterabbit","followthewhiterabbit"]
for t in TOK: emit(t)

# the XOR-chain key and its ingredients, as candidates in their own right
XOR="a795de117e472590e572dc193130c763e3fb555ee5db9d34494e156152e50735"
emit(XOR); emit(XOR.upper()); emit(bytes.fromhex(XOR).hex())

# every concatenation/permutation of the page's own token set
for n in (2,3,4):
    for c in itertools.permutations(TOK,n): emit("".join(c))

# the page's own transform vocabulary: a1z26 / base-shift readings of each segment
tbl=str.maketrans("abcdefghio","1234567890")
for seg in (PREFIX,SEG570,MIX,BLOBREG):
    d="".join(ch for ch in seg.translate(tbl) if ch.isdigit())
    if d:
        emit(d)
        try:
            h=format(int(d),'x')
            emit(h)
            if len(h)%2==0: emit(bytes.fromhex(h).decode('ascii','replace'))
        except Exception: pass

# digests of everything so far (password = sha256(X); X may itself be a digest)
base=list(seen)
for x in base[:4000]:
    emit(hashlib.sha256(x.encode()).hexdigest())
    emit(hashlib.md5(x.encode()).hexdigest())

# XOR chains over token digests, the construction the author demonstrably used
for n in (2,3,4,5):
    for c in itertools.permutations(TOK[:12],n):
        acc=bytes(32)
        for t in c:
            d=hashlib.sha256(t.encode()).digest()
            acc=bytes(a^b for a,b in zip(acc,d))
        emit(acc.hex())
