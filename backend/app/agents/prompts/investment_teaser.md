You are writing a 1-page investment teaser for a business based on its simulation results.

SIMULATION DATA:
{{ data_json }}

OUTPUT STRUCTURE (InvestmentTeaser schema):
- problem: 1-2 sentences describing the market problem
- solution: 1-2 sentences describing the product/solution
- simulated_survival: cite the exact survival_rate from data
- key_metrics: 3-4 bullet strings using exact numbers from data (MRR, CAC, LTV/CAC, runway)
- ask: 1 sentence describing the funding ask (derive from starting_capital and burn rate)
- risks: top 2 risks from architectural_weaknesses

RULES:
- Every number must come from the simulation data. Never fabricate.
- Tone: confident but realistic.
