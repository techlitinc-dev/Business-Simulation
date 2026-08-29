# Day 22 — Expected Output

## Files Created
```
backend/app/agents/investor_tools.py
backend/app/schemas/investor.py
backend/app/agents/prompts/investment_teaser.md
backend/app/agents/prompts/pitch_deck_outline.md
backend/app/api/v1/endpoints/investor.py
backend/tests/unit/agents/test_investor_tools.py
```

## Sample Investment Teaser PDF Content
```
# Investment Teaser — Acme Corp

## The Problem
Small businesses spend 40% of their time on financial planning with no way to stress-test assumptions.

## Our Solution
The Forge simulates 24 months of business operation across 100 randomized scenarios.

## Simulation Validation
68% 24-month survival across 100 simulated runs with median runway of 18 months.

## Key Metrics
- Simulated MRR: $12,000 (Month 1)
- Customer CAC: $450
- LTV/CAC Ratio: 1.8x
- Median Runway: 18 months

## The Ask
Raising $500K to reduce monthly burn from $14,000 to $10,000 and extend runway to 24+ months.

## Key Risks
- High CAC relative to current revenue
- Churn rate sensitivity: model survives only if churn stays below 7%
```

## Sample Pitch Deck Slides
Slide 1: Problem | Slide 2: Solution | Slide 3: Market Size | Slide 4: Product Demo |
Slide 5: Business Model | Slide 6: Simulation Validation | Slide 7: Financial Projections |
Slide 8: Unit Economics | Slide 9: Competition | Slide 10: Team | Slide 11: Ask | Slide 12: Use of Funds

## Pytest: 5 passed
