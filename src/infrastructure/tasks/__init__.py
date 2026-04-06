"""Background task workers for Einstein's 3-tier processing pipeline.

Workers:
  - tier1_worker: Generate embeddings for unprocessed context events
  - tier2_worker: LLM enrichment (topics, action items, entity refinement)
  - connection_worker: Discover links between events (entity match, temporal, semantic)
  - insight_worker: Generate briefings, detect dormancy, trigger resurfacing
"""
