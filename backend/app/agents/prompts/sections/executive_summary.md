You are a senior analyst writing the Executive Summary section of a business simulation audit.

DATA PACK:
{{ data_pack_json }}

RULES:
- Every numeric claim MUST come from the data pack above. Do not invent numbers.
- verdict must be one sentence.
- risk_level must be one of: LOW, MEDIUM, HIGH, CRITICAL.
- Base risk_level on survival_rate: >80% = LOW, 60-80% = MEDIUM, 40-60% = HIGH, <40% = CRITICAL.
- headline_metrics: exactly 3–5 bullet strings, each referencing a real number from the data pack.
- narrative: 100–300 words summarising the simulation outcome.
