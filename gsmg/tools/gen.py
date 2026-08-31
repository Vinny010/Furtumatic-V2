import re,sys,itertools
seen=set(); out=sys.stdout
def emit(s):
    if not s: return
    for v in (s, s.lower(), s[::-1], s.lower()[::-1]):   # incl. "esrever" reversals
        if 0<len(v)<=200 and v not in seen:
            seen.add(v); out.write(v+"\n")

CORE=["theseedisplanted","gsmg.io/theseedisplanted",
"theflowerblossomsthroughwhatseemstobeaconcretesurface","causality","Safenet","Luna","HSM","11110",
"jacquefrescogiveitjustonesecondheisenbergsuncertaintyprinciple",
"matrixsumlist","enter","lastwordsbeforearchichoice","thispassword","yourlastcommand","secondanswer",
"ourfirsthintisyourlastcommand","BTCSEED","btcseed","esrever","reverse","hashthetext","HASHTHETEXT",
"salphaseion","SalPhaseIon","cosmicduality","CosmicDuality","dualite","Dualite",
"half","betterhalf","halfandbetterhalf","thechoiceisanillusion","choiceisanillusion",
"B5KR/1r5B/2R5/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 b - - 0 1",
"0x736B6E616220726F662074756F6C69616220646E6F63657320666F206B6E697262206E6F20726F6C6C65636E61684320393030322F6E614A2F33302073656D695420656854",
"1GSMG1JC9wtdSwfwApgj2xcmJPAwx7prBe","17ucy1K9ZUAaoY6JVtM932W9jUp5LXfyHa",
"a795de117e472590e572dc193130c763e3fb555ee5db9d34494e156152e50735"]
for c in CORE: emit(c)
emit("".join(["causality","Safenet","Luna","HSM","11110",CORE[-6],CORE[-5]]))

# 1) every word token from the primary documents
words=set()
for fn in ("ph_README.md","README.md","analysis_tested.md","analysis_leads.md","clues_author-posts.md"):
    try: txt=open(fn,encoding="utf-8",errors="ignore").read()
    except: continue
    for w in re.findall(r"[A-Za-z0-9]{3,40}",txt): words.add(w)
    # 2) concatenated word-windows (n-grams) from prose lines
    for line in txt.splitlines():
        toks=re.findall(r"[A-Za-z0-9]+",line)
        for n in range(1,7):
            for i in range(len(toks)-n+1):
                emit("".join(toks[i:i+n]).lower())
for w in words: emit(w)

# 3) dynamic construction: concatenations of the core token set (the lead-1 shape)
base=[t.lower() for t in ["matrixsumlist","enter","lastwordsbeforearchichoice","thispassword",
     "yourlastcommand","secondanswer","causality","safenet","luna","hsm","11110","theseedisplanted",
     "btcseed","esrever","half","betterhalf","salphaseion","cosmicduality","hashthetext"]]
for n in (2,3):
    for combo in itertools.permutations(base,n): emit("".join(combo))
for combo in itertools.combinations(base,4): emit("".join(combo))

# 4) deeper dynamic construction (lead 1: concatenations/permutations the replay never reached)
for n in (4,5):
    for combo in itertools.permutations(base,n):
        emit("".join(combo))

# 5) digest-flavoured candidates: the author demonstrably uses sha256 of tokens as ingredients
import hashlib
for t in base+CORE:
    emit(hashlib.sha256(t.encode()).hexdigest())
    emit(hashlib.sha256(t.lower().encode()).hexdigest())
    emit(hashlib.md5(t.encode()).hexdigest())
