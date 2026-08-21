You are writing a reusable business playbook from a post-mortem simulation analysis.

A playbook is a repeatable play for a recurring business situation — not a
one-off report. It should be actionable by a founder who has never seen this
simulation.

Analyze the DATA block, then output ONLY the Playbook JSON with these fields:

- "title": a short, evocative title (e.g. "Surviving a Demand Shock as a
  Subscription Business")
- "scenario_type": the class of situation (market / operational / financial /
  black_swan / internal)
- "situation": 2-3 sentences on when to use this playbook
- "steps": 3-10 ordered action steps
- "key_metrics_to_watch": at least 2 metrics that signal the situation is
  improving or worsening
- "expected_outcome": what the founder should expect if the steps are followed
- "source_run_summary": 1 sentence summarizing the run this playbook came from

Ground every step in the data provided. NEVER invent figures — reference only
the numbers in DATA.

DATA:
{{ data_json }}
