# AI Mathematical Olympiad (AIMO) Prize — state as of 21 Sept 2026

Sourcing caveat: the egress proxy blocked direct fetches of aimoprize.com, xtxmarkets.com, kaggle.com, huggingface.co, arxiv.org, mathstodon.xyz, blogs.nvidia.com and competehub.dev. Facts from those domains below come from search-result snippets of those pages (URL cited) rather than a full page read, and are marked "(snippet)". GitHub pages were fetched in full.

## Q1. Current status of Progress Prizes 1–3 (and any 4th) and the $5M Grand Prize; what is open; deadlines

### Takeaway
All three Progress Prizes have concluded (AIMO1 July 2024, AIMO2 April 2025, AIMO3 April 2026, winners announced June 2026). There is no Progress Prize 4 and there will not be one: XTX Markets announced in its 2026 philanthropy update that it has **closed the AIMO Prize, including not progressing with the $5M Grand Prize**. As of September 2026 nothing is open and there are no deadlines; the Grand Prize was never awarded.

### Cited Findings
- XTX Markets launched the AIMO Prize in Nov 2023 as a $10M fund: a $5M grand prize for "the first publicly shared AI model to enter an AIMO approved competition and perform at a standard equivalent to a gold medal in the IMO", plus progress prizes "totalling up to $5 million". Eligibility "requires the open publication of the teams' code, methodology, data, and model parameters." — [PR Newswire, Nov 2023](https://www.prnewswire.com/news-releases/xtx-markets-launching-10-million-artificial-intelligence-mathematical-olympiad-prize-301997891.html)
- Progress Prize 1 ran April 1 – June 27, 2024 with a $1.048M pool; Progress Prize 2 opened Oct 2024 with a $2.1M pool and 110 problems at "around National Olympiad level". — [aimoprize.com first-prize announcement (snippet)](https://aimoprize.com/updates/2024-04-02-progress-prize); [aimoprize.com participate page (snippet)](https://aimoprize.com/participate)
- Progress Prize 2 closed April 2025; "NemoSkills as the top team on the final Kaggle leaderboard, achieving a score of 34/50" after "a closely contested six-month competition". — [aimoprize.com "Second Progress Prize closed" (snippet)](https://aimoprize.com/updates/2025-04-15-second-progress-prize-closed)
- Progress Prize 3 launched on Kaggle 19 Nov 2025 with "Prizes totaling $2,207,152", 110 original problems "ranging from National Olympiad level to International Mathematical Olympiad (IMO) standard", and "H100s ... available for both training and testing via Kaggle". — [aimoprize.com AIMO3 launch (snippet)](https://aimoprize.com/updates/2025-11-19-third-progress-prize-launched)
- AIMO3 deadlines: entry deadline April 8, 2026; final submission deadline April 15, 2026. — [Kaggle on X, Nov 2025](https://x.com/kaggle/status/1991530429955076427); [aimoprize.com (snippet)](https://aimoprize.com/updates/2025-11-19-third-progress-prize-launched)
- AIMO3 winners announced June 2026: "Exalted Joseph, varianceofx, SKobayak, TAMU-TACO and yemao ye, representing the #1, #2, #3, #5 and #7 ranked participants, respectively." Winners were to showcase models at "AI Day at the 2026 IMO in Shanghai, China." — [aimoprize.com updates (snippet)](https://aimoprize.com/updates/)
- **Closure:** "after careful consideration, including taking views from the AIMO Prize Advisory Committee, XTX Markets has decided to close the AIMO Prize, including not progressing with the Grand Prize." Over the series: "6,829 teams, 8,145 participants, 274,576 submissions, with approximately $1,619,760 awarded out of $5,582,880 advertised." XTX says it "convened a group of 40 leading maths educators and researchers" this summer to draft "a blueprint for developing the mathematicians of the future" and is redirecting investment there. — [XTX Markets, "Update on XTX Markets' AI for Maths Philanthropy" (snippet)](https://www.xtxmarkets.com/news/2026-update-on-xtx-markets-ai-philanthropy/)
- No search returned any "Progress Prize 4" announcement; the most recent competition is AIMO3. — [search across aimoprize.com/Kaggle, Sept 2026](https://aimoprize.com/updates/)

### Inferences
- $5,582,880 advertised ≈ $1,048,576 (AIMO1) + ~$2.1M (AIMO2) + $2,207,152 (AIMO3) + smaller extras; it excludes the $5M grand prize, i.e. XTX never "advertised" the grand prize as an active competition, and the ~$1.62M actually paid is roughly 29% of what was advertised. The remainder was tied to unreached score thresholds (see Q2/Q3).
- The closure language ("This summer ... convened") implies the update was published in late summer 2026, after the AIMO3 winners were announced in June 2026 and after IMO 2026 (July). Exact publication date not visible in snippets.
- With the prize closed, the expected monetary value of preparing an AIMO entry now is zero unless a successor competition appears; only Kaggle medals/rank (non-monetary) remain from past events.

### Gaps
- Exact publication date of the XTX closure notice and its full reasoning could not be read (xtxmarkets.com blocked). Whether XTX retains any option to re-open or fund a successor is unknown.
- The aggregate "8,145 participants" in XTX's update vs "22,858 entrants, 4,133 teams, 60,050 submissions" reported for AIMO3 alone (see Q5) cannot be reconciled without the source pages; likely different definitions (Kaggle "entrants" who joined vs teams that submitted).

## Q2. Who won so far (individuals vs teams vs companies), backgrounds, and actual payouts per place

### Takeaway
AIMO1 was won by Project Numina (a 16-author collaboration incl. Hugging Face staff and Mistral/OpenAI-affiliated researchers); AIMO2 by NVIDIA's "NemoSkills" team of Kaggle grandmasters (prize donated to NVIDIA Foundation); AIMO3 by "Exalted Joseph" (linked to a Hugging Face bucket "SWIFTx-AI") with "varianceofx", "SKobayak", "TAMU-TACO" and "yemao ye" taking the other paid slots. Top-place money in AIMO2 and AIMO3 was $262,144 / $131,072 / $65,536 / $32,768 / $16,384 for places 1–5, plus ~$110K of side prizes in AIMO3; only about $1.62M of $5.58M advertised was ever paid.

### Cited Findings
- AIMO1 winner: Project Numina, fine-tuning DeepSeekMath-Base 7B into NuminaMath-7B-CoT / -TIR; authors listed: Jia Li, Edward Beeching, Lewis Tunstall, Ben Lipkin, Roman Soletskyi, Shengyi Costa Huang, Kashif Rasul, Longhui Yu, Albert Jiang, Ziju Shen, Zihan Qin, Bin Dong, Li Zhou, Yann Fleureau, Guillaume Lample, Stanislas Polu. — [project-numina/aimo-progress-prize GitHub](https://github.com/project-numina/aimo-progress-prize); [PR Newswire, July 2024](https://www.prnewswire.com/news-releases/first-ai-mathematical-olympiad-progress-prize-won-by-team-numina-302202594.html)
- AIMO2 winner: NVIDIA team "NemoSkills" — "solved 34 out of 50 problems in just 5 hours using 4 L4 GPUs"; team includes Christof Henkel, Darragh Hanley, Ivan Sorokin (and others). — [NVIDIA AI Developer on X, Apr 2025](https://x.com/NVIDIAAIDev/status/1910383538027061764)
- AIMO2 prize table: 1st $262,144; 2nd $131,072; 3rd $65,536; 4th $32,768; 5th $16,384. NemoSkills "won the $262,144 prize that they directed to the NVIDIA Foundation to support charitable organizations." — [NVIDIA blog (snippet)](https://blogs.nvidia.com/blog/reasoning-ai-math-olympiad/); [aimoprize.com "Second Progress Prize closed" (snippet)](https://aimoprize.com/updates/2025-04-15-second-progress-prize-closed)
- AIMO3 prize table: total $2,207,152; "Prizes for top-ranking teams range from $262,144 for 1st place to $16,384 for 5th place. Additional prizes, totaling $110,000, are available for the Longest Leader Prize, Hard Problem Prize, Math Corpus Prize, and Writeup Prizes." — [Kaggle AIMO3 competition page (snippet)](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3)
- AIMO3 paid winners: Exalted Joseph (#1), varianceofx (#2), SKobayak (#3), TAMU-TACO (#5), yemao ye (#7). Math Corpus Prize: Yi-Chia Chen. — [aimoprize.com updates (snippet)](https://aimoprize.com/updates/)
- AIMO3 1st-place solution "written by Exalted Joseph and uploaded to Huggingface" at huggingface.co/buckets/SWIFTx-AI/data, with Kaggle notebook and code made public. — [Kaggle 1st-place write-up (snippet)](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/writeups/1st-place-solution-for-the-aimo3-competition)
- AIMO3 2nd place published a model "varianceofx/aimo3-2nd-place-solver-adapted" on Hugging Face. — [Hugging Face listing (snippet)](https://huggingface.co/varianceofx/aimo3-2nd-place-solver-adapted)
- Series total paid: "approximately $1,619,760 awarded out of $5,582,880 advertised." — [XTX Markets 2026 update (snippet)](https://www.xtxmarkets.com/news/2026-update-on-xtx-markets-ai-philanthropy/)

### Inferences
- AIMO3's paid list skipping ranks #4 and #6 strongly suggests those teams were disqualified from prize money (most likely for failing the open-source/licensing or code-verification requirements), so finishing top-5 on the leaderboard did not guarantee a payout.
- Arithmetic: top-5 in AIMO2 = $507,904; top-5 in AIMO3 = $507,904 + up to $110,000 extras ≈ $618K. That leaves roughly $490K for AIMO1 top-5 plus AIMO1/AIMO2 side prizes to reach XTX's ~$1.62M total — consistent with AIMO1's top prize being about half AIMO2's (the pool was half the size). Across all three events the number of distinct prize-receiving entries is on the order of 15 top-5 slots plus a handful of side prizes (~20–25 payouts total out of 6,829 teams).
- Winner profile trend: AIMO1 = well-funded open-source collaboration with H100 training; AIMO2 = corporate (NVIDIA) grandmaster team; AIMO3 = the top three names are Kaggle handles rather than lab teams, and the #1 write-up on Kaggle plus a Hugging Face upload indicates individual/small-team winners — but their affiliations could not be verified (see Gaps).
- The "TAMU-TACO" name suggests a Texas A&M University group; unverified.

### Gaps
- AIMO1 exact per-place amounts and Numina's final score (29/50 in my recollection) and the names of AIMO1 places 2–5 could not be retrieved from a fetchable source (aimoprize.com/huggingface.co blocked); treat as unverified.
- Backgrounds/affiliations of the AIMO3 winners (Exalted Joseph / SWIFTx-AI, varianceofx, SKobayak, yemao ye) could not be established; the Kaggle write-ups were unreachable.
- Exact split of the $110,000 AIMO3 side prizes and who won Longest Leader / Hard Problem / Writeup prizes is unknown.

## Q3. What winning technically required: models, compute, Kaggle hardware limits, open-source requirement, time

### Takeaway
Winning moved from "fine-tune a 7B model on 8×H100 for 10 hours and serve on T4s" (AIMO1) to "run an off-the-shelf 120B open model (gpt-oss-120b) on Kaggle's free H100s within a 5-hour, 50-problem budget with heavy inference engineering (parallel sampling, tool-integrated Python, weighted voting)" (AIMO3). The differentiator in AIMO3 was inference-time system design and prompt/agent engineering rather than owning training compute, but the required model sizes (120B) exceed what fits on one or two RTX 4090s without aggressive quantization.

### Cited Findings
- AIMO1 (2024): Numina fine-tuned DeepSeekMath-Base 7B; "On one node of 8 x H100 GPUs, our models took 10 hours to train"; models "quantized to 8-bit precision ... to improve performance with vLLM on Kaggle's T4 GPUs." — [project-numina/aimo-progress-prize](https://github.com/project-numina/aimo-progress-prize)
- AIMO2 (2024–25): Kaggle inference budget was 4× L4 GPUs and 5 hours for 50 problems; NemoSkills solved 34/50 in that budget. — [NVIDIA AI Developer on X](https://x.com/NVIDIAAIDev/status/1910383538027061764)
- AIMO3 (2025–26): Kaggle provided H100s "for both training and testing"; "GPU Notebook run-time should be <= 5 hours." — [aimoprize.com launch (snippet)](https://aimoprize.com/updates/2025-11-19-third-progress-prize-launched); [Kaggle AIMO3 page (snippet)](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3)
- AIMO3 answers are "5-digit integers (0–99999)"; a bronze-medal solo entry used "GPT-OSS 120B served locally via vLLM", fp8 KV cache, "900 seconds per problem maximum; 17,400 seconds total notebook budget", 8 parallel attempts per problem with entropy-weighted voting and a live Jupyter/sympy sandbox. — [tanishmohokar/AIMO-Progress-Prize-3 GitHub](https://github.com/tanishmohokar/AIMO-Progress-Prize-3)
- A high-ranking (non-prize) solo AIMO3 entry: "GPT-OSS 120B (Unsloth-quantized) via vLLM" — "the Unsloth quantization was critical—it enabled the 120B model to fit within Kaggle's GPU memory constraints"; "5 hours total for all 50 problems (~6 minutes per problem average)"; 16 Jupyter kernels + vLLM with tensor parallelism; 8 samples/problem with early stop at 4-way consensus; dynamic time bank; weighted voting penalising answers without Python verification; two-layer RAG over 41 technique cards + 20K OpenMathReasoning problems. Public LB 38/50, "final score 41.5/50". MCTS/beam search and cooperative "classroom pooling" did not help; template changes caused a −14 point regression. Author notes "simpler prompts with a stronger model likely preferable." — [Jarvis2001/AIMO3-Writeup GitHub](https://github.com/Jarvis2001/AIMO3-Writeup)
- Community notebooks show gpt-oss-120b running the full AIMO3 test in ~3 hours on Kaggle H100. — [Kaggle notebook (title only)](https://www.kaggle.com/code/seshurajup/aimo-3-gpt-oss-120b-3hours-wow-h100)
- Open-source rule (all prizes): "Eligibility for prizes requires the open publication of the teams' code, methodology, data, and model parameters." — [PR Newswire, Nov 2023](https://www.prnewswire.com/news-releases/xtx-markets-launching-10-million-artificial-intelligence-mathematical-olympiad-prize-301997891.html)
- The prize-threshold for the full "Overall Progress Prize" pool was 47/50 on the final leaderboard (never reached in any edition). — [Kaggle write-up (snippet)](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/writeups/entropy-weighted-majority-voting-with-gpt-oss-120b); AIMO2 top score 34/50 per [aimoprize.com (snippet)](https://aimoprize.com/updates/2025-04-15-second-progress-prize-closed)

### Inferences
- Because Kaggle supplied the inference hardware (H100s) for free in AIMO3, owning GPUs mattered mainly for offline iteration (running gpt-oss-120b locally to test pipelines) and for any fine-tuning. gpt-oss-120b in 4-bit needs roughly 60–80 GB of VRAM, which does not fit on one RTX 4090 (24 GB) and is marginal even on two; solo competitors who did local development mostly relied on Kaggle's H100 quota or rented cloud GPUs. (Memory figure is general knowledge, not from a fetched source.)
- The strongest AIMO3 entries appear to be engineering-heavy agentic inference pipelines around gpt-oss-120b rather than custom-trained models, so consumer-GPU competitors were not compute-locked out in principle, but the score ceiling of the shared base model meant many teams converged to similar scores and the top-5 separation came from tuning, luck on the private set, and verification rigor.
- Time invested by top entrants was large: the Jarvis2001 write-up documents dozens of pipeline versions (V38 referenced) with unit-tested modules — a multi-month effort.

### Gaps
- The exact model/training recipe of the AIMO3 #1–#3 solutions (whether they fine-tuned gpt-oss-120b or another model, and how much training compute they used) could not be read (Kaggle/Hugging Face blocked).
- Kaggle's weekly free H100 quota during AIMO3 (hours per week per user) was not found.
- The AIMO3 final leaderboard scores of the paid winners were not found; a community notebook titled "[44/50] AIMO3: Skills optional, Luck required" exists but is by a different user (nihilisticneuralnet) and is a public-LB score, not the winner's — [Kaggle notebook](https://www.kaggle.com/code/nihilisticneuralnet/44-50-aimo3-skills-optional-luck-required).

## Q4. Has the $5M Grand Prize been claimed or is it close? Frontier-lab IMO gold and its effect

### Takeaway
The Grand Prize was never awarded and now cannot be: XTX closed the prize without progressing it. Ironically, the technical bar has since been met by open models — NVIDIA's Nemotron 3 Ultra system scored 30/42 (gold threshold 29) at IMO 2026 with fully released weights/data/code, and DeepSeek V4 Flash was reported at 30/42 — following closed-model gold (OpenAI and Google DeepMind, 35/42) at IMO 2025 and perfect 42/42 scores by Huawei and Xiaohongshu models at IMO 2026.

### Cited Findings
- Grand prize condition: $5M "to the first publicly-shared AI model to enter an AIMO approved competition and perform at a standard equivalent to a gold medal in the IMO." — [PR Newswire, Nov 2023](https://www.prnewswire.com/news-releases/xtx-markets-launching-10-million-artificial-intelligence-mathematical-olympiad-prize-301997891.html)
- XTX "decided to close the AIMO Prize, including not progressing with the Grand Prize." — [XTX Markets 2026 update (snippet)](https://www.xtxmarkets.com/news/2026-update-on-xtx-markets-ai-philanthropy/)
- AIMO's own framing at AIMO3 launch: "Recent breakthroughs by closed-source models achieving gold medal performance at the 2025 IMO demonstrate that AI is approaching human-level capability of mathematical reasoning." — [aimoprize.com (snippet)](https://aimoprize.com/updates/2025-11-19-third-progress-prize-launched)
- IMO 2025: Google DeepMind and OpenAI "both earning 35 out of 42 points" (gold level); "DeepSeek-Math-V2 later reached the same gold level as an open-weight model in November 2025." — [KuCoin news summary](https://www.kucoin.com/news/flash/china-wins-2026-imo-with-full-marks-shanghai-high-school-shines); see also [Zvi, "Google and OpenAI Get 2025 IMO Gold"](https://thezvi.substack.com/p/google-and-openai-get-2025-imo-gold) and [LessWrong, "OpenAI Claims IMO Gold Medal"](https://www.lesswrong.com/posts/RcBqeJ8GHM2LygQK3/openai-claims-imo-gold-medal)
- IMO 2026 (Shanghai, July 13–21, 2026): "Huawei's Celia and Xiaohongshu's dots-note 3.0 each achieved an officially graded perfect 42/42." — [SCMP](https://www.scmp.com/tech/article/3361482/worlds-first-ai-model-earn-perfect-score-maths-olympiad-comes-chinas-rednote); [Tech Insider](https://tech-insider.org/ai-imo-2026-perfect-score-odds-hit-96-percent/)
- NVIDIA, "An Open Recipe for IMO Gold: Training Nemotron for Olympiad Mathematics" (arXiv 2609.10712, Sept 2026): "scored 30 out of 42 points at IMO 2026, reaching the gold-medal threshold"; three Nemotron 3 Ultra checkpoints in a generate–verify–refine search, "entirely in natural language, with no formal prover, external tools, or internet access"; authors "released the two post-trained checkpoints as well as the training data, the training and inference code, the submitted solutions, and Nemotron-IMO-Bench." — [arXiv abstract (snippet)](https://arxiv.org/abs/2609.10712)
- DeepSeek V4 Flash "hit 30/42, clearing the 29-point gold cutoff" without olympiad-specific post-training. — [Cline blog](https://cline.bot/blog/deepseek-wins-imo-gold-on-12-cents)
- Ethan Mollick called this "the first time that an open model has reported gold-medal level status at the IMO." — [Mollick on X](https://x.com/emollick/status/2079944833599156569); this conflicts with the KuCoin summary crediting DeepSeek-Math-V2 with open-weight gold in Nov 2025 (the latter was retroactive on IMO 2025 problems rather than live entry).

### Inferences
- The grand prize's formal condition ("enter an AIMO approved competition") was never operationalised — no AIMO-approved gold-level competition was ever run — so open-model IMO gold achieved outside AIMO (Nemotron, DeepSeek) could not have claimed it even before the closure.
- Plausible reason for closure (inference, not stated in snippets): once frontier labs and then open-weight models achieved IMO gold on their own in 2025–26, the prize lost its purpose as an incentive, and the AIMO3 top scores were still far below the 47/50 full-prize threshold.

### Gaps
- XTX's explicit stated rationale for closing the grand prize could not be read in full.
- Whether any partial/consolation award was made to Nemotron/DeepSeek or others under the grand-prize fund — no evidence found; the ~$1.62M total paid suggests none.

## Q5. Realistic score/rank for a solo competitor with consumer GPUs (leaderboard distributions, write-ups)

### Takeaway
In AIMO3, 4,133 teams competed and only 5 leaderboard slots (plus ~4 side prizes) paid; publicly shared gpt-oss-120b pipelines put a diligent solo competitor around 38–41/50, i.e. medal range but not top-5, and one 44/50 public-LB notebook was self-described as "Skills optional, Luck required" (public-LB noise). Kaggle's free H100s meant consumer GPUs were not the binding constraint — engineering time, evaluation rigor and private-set luck were. Going forward, the question is moot for money: the prize is closed.

### Cited Findings
- AIMO3 scale: "22,858 entrants, 4,133 teams, and 60,050 submissions." — [aimoprize.com updates (snippet)](https://aimoprize.com/updates/)
- Series scale: "6,829 teams, 8,145 participants, 274,576 submissions" with ~$1,619,760 paid. — [XTX Markets 2026 update (snippet)](https://www.xtxmarkets.com/news/2026-update-on-xtx-markets-ai-philanthropy/)
- Solo AIMO3 entrant using gpt-oss-120b + TIR + RAG: public 38/50, final 41.5/50, did not place in top 5. — [Jarvis2001/AIMO3-Writeup](https://github.com/Jarvis2001/AIMO3-Writeup)
- Solo bronze-medal AIMO3 entrant using gpt-oss-120b, 8 parallel attempts, entropy-weighted voting. — [tanishmohokar/AIMO-Progress-Prize-3](https://github.com/tanishmohokar/AIMO-Progress-Prize-3)
- A public notebook scoring 44/50 on the public leaderboard is titled "Skills optional, Luck required." — [Kaggle notebook](https://www.kaggle.com/code/nihilisticneuralnet/44-50-aimo3-skills-optional-luck-required)
- Baseline "Entropy-Weighted Majority Voting with gpt-oss-120b" was a widely shared AIMO3 approach. — [Kaggle write-up (title/snippet)](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/writeups/entropy-weighted-majority-voting-with-gpt-oss-120b)
- AIMO2 top score was 34/50 (NVIDIA, 4×L4, 5 h); AIMO2 problems were reused to benchmark closed models, where OpenAI o3 beat the open-source winner by ~5 points. — [aimoprize.com "The gap is shrinking", Sept 2025 (snippet)](https://aimoprize.com/updates/2025-09-05-the-gap-is-shrinking); [36kr summary](https://eu.36kr.com/en/p/3457470805284482)
- Full-prize threshold 47/50 was never reached in any edition. — [Kaggle write-up (snippet)](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/writeups/entropy-weighted-majority-voting-with-gpt-oss-120b)

### Inferences
- Odds framing for AIMO3: 5 paid leaderboard slots / 4,133 teams ≈ 0.12% of teams got main-prize money; adding side prizes ≈ 0.2%. The Kaggle medal tiers (gold ≈ top ~0.5–1%, silver/bronze deeper) were reachable for a strong solo entrant, but carry no money.
- A solo competitor with 1–2 RTX 4090s would have been in the same position as the solo write-ups above: able to reach ~38–42/50 by adapting public gpt-oss-120b pipelines on Kaggle's H100 quota, with the gap to the top 5 determined by months of inference-engineering iteration and private-LB variance rather than by local GPU capacity. Local 4090s would mainly serve for smaller-model experiments (≤30B in 4-bit) since gpt-oss-120b needs far more VRAM.
- Since the prize series is closed with no successor announced, there is no realistic path to AIMO money as of Sept 2026; any "paid math problems" thesis based on AIMO must rely on other sponsors or competitions.

### Gaps
- Full AIMO3 private leaderboard distribution (median score, medal cutoffs, scores of ranks 1–10) could not be retrieved (Kaggle blocked).
- No public data on how many AIMO3 top-50 entries were solo vs team vs lab-affiliated.
- No source found on the size of Kaggle's free H100 allowance for AIMO3 participants, which determined how much offline iteration a solo competitor could do without owning GPUs.
