# AI Master Guidelines

## LLM Application Architecture

### Core Patterns

#### RAG (Retrieval-Augmented Generation)
```
Query → Embed → Vector Search → Context → LLM → Answer
                ↑
         Knowledge Base
```

Key decisions:
- Chunking strategy (size, overlap, semantic)
- Embedding model (cost vs quality)
- Vector DB selection
- Retrieval: dense, sparse, hybrid
- Reranking for precision

#### Agent Systems
```
Goal → Planner → [Tool 1, Tool 2, ...] → Executor → Result
                    ↑              ↓
               Memory         Observation
```

Key components:
- Planning (reactive vs proactive)
- Tool definitions (schemas, descriptions)
- Memory (short-term, long-term, episodic)
- Evaluation/guardrails

#### Prompt Engineering

### Structure
```
[System Prompt]
[Context / Few-shot Examples]
[User Query]
[Output Format Instructions]
```

### Techniques
- Chain-of-thought for reasoning
- Structured output (JSON, function calling)
- Self-consistency (multiple samples)
- Tree-of-thoughts for complex problems
- Constitutional AI for safety

## Model Selection

| Use Case | Recommendation |
|----------|----------------|
| General chat | GPT-4o, Claude 3.5 Sonnet |
| Coding | GPT-4o, Claude 3.5 Sonnet, DeepSeek |
| Reasoning | o1, o3-mini, Claude 3.5 Sonnet |
| Cost-sensitive | GPT-4o-mini, Haiku, Llama 3.1 |
| Local/Private | Llama 3.1, Qwen 2.5, Phi-3 |
| Multimodal | GPT-4o, Gemini 1.5, Claude 3.5 |

## Production Considerations

### Observability
- Token usage tracking
- Latency percentiles
- Error rates by type
- Quality evaluation (auto + human)
- Cost per interaction

### Safety
- Input validation/sanitization
- Output filtering
- PII detection/redaction
- Prompt injection defense
- Rate limiting per user

### Evaluation
- Golden dataset for regression
- A/B testing for prompt changes
- Human feedback loops
- Automated quality gates

### Cost Optimization
- Model routing (simple → cheap, complex → capable)
- Caching (semantic, exact)
- Prompt compression
- Batch processing where possible
