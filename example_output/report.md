# RAG Comparison

## Summary
Naive RAG is the simplest baseline: retrieve chunks and answer from them. Sentence-window retrieval preserves local context around a matching sentence. Parent-child retrieval links small retrieval units to larger parent sections for richer context.

## Key findings
- **Naive RAG** is easiest to implement and cheapest to run, but it often loses context when chunks are too small.
- **Sentence-window retrieval** improves factual grounding around a matched sentence without fetching an entire long chunk.
- **Parent-child retrieval** is strong for long structured documents because it retrieves with small units and answers with larger sections.

## Conclusion
For many production cases, sentence-window retrieval is a practical default. Parent-child retrieval is stronger for large structured corpora, while naive RAG remains a useful baseline.

## Sources
- Example source 1 — https://example.com/rag-basics
- Example source 2 — https://example.com/sentence-window
- Example source 3 — https://example.com/parent-child
