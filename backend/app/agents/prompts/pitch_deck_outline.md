You are creating a 10-12 slide pitch deck outline grounded in business simulation data.

SIMULATION DATA:
{{ data_json }}

OUTPUT STRUCTURE (PitchDeckOutline schema):
- slides: list of 10-12 slides, each: {slide_number, title, talking_points: list[str]}
- Each talking_point must reference a real number or finding from the simulation data.

Standard slide order: Problem, Solution, Market, Product, Business Model, Traction/Simulation,
Financial Projections, Unit Economics, Competition, Team (placeholder), Ask, Use of Funds.
