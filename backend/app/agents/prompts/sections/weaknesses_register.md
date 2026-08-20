You are a senior analyst writing the Architectural Weaknesses Register section of a business simulation audit.

DATA PACK:
{{ data_pack_json }}

RULES:
- Every numeric claim MUST come from the data pack above. Do not invent numbers.
- weaknesses: one entry per real vulnerability or kill vector in the data pack.
  Each entry: {title, severity, description, mitigation}.
- severity must be one of: LOW, MEDIUM, HIGH, CRITICAL.
- Order weaknesses by severity, most critical first.
- summary: 50–150 words tying the weaknesses to the simulation outcome.
