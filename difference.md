Good concrete question.
Easy to call: OpenWeatherMap API

Single endpoint
Parameters map directly to natural language ("city=London&units=metric")
Returns one JSON object, no pagination
No cross-referencing other APIs
The "correct" answer is obvious and verifiable

An LLM basically can't mess this up.

Hard to call: NCBI (from the paper)

3 separate APIs (REST, Datasets, E-utilities) that need to be combined for one query
Pagination required for large result sets, and the agent must know when it's done
Some filters only work server-side, others must be applied locally after downloading
Metadata fields mean different things depending on context (e.g. "complete genome" means something different for segmented vs. non-segmented viruses)
No easy way to verify if the result is correct — 15 sequences looks plausible even when the answer is 266

The LLM has to make 5-6 independent decisions correctly in sequence, and a wrong call at any step silently produces a wrong-looking-right answer.

The key distinction isn't really complexity of parameters — it's whether errors are visible. OpenWeatherMap returns obviously wrong data if you mess up. NCBI returns plausible-but-incomplete data, which is much harder for an LLM (or a human) to catch.You said: Ok but you have not answer my question (previous than this one) abt well written software