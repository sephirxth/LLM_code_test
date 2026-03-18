# LLM Code Test

Benchmark comparing LLM code generation quality across models and prompting strategies. Tests Claude, Gemini, GPT, Grok, and DeepSeek on a standardized physics simulation task.

## What It Tests

All models receive the same prompt: implement a Python physics simulation (bouncing balls in a rotating heptagon with gravity, collision detection, and real-time rendering). This tests:

- **Physics accuracy** — Collision detection, coordinate transforms, energy conservation
- **Code completeness** — Full runnable program vs. partial snippets
- **Architecture quality** — Code structure, modularity, readability

## Key Findings

| Model | META Prompt | Canvas/Artifact | Result |
|-------|-------------|-----------------|--------|
| Claude Opus 4.5+ | Yes | N/A | Best overall |
| Claude Opus 4 | Yes | N/A | Strong |
| Gemini 3.0 Pro | Yes | No | Good |
| Gemini 2.5 Pro | Yes | Canvas hurts | Canvas degrades quality |
| DeepSeek R1 | N/A | N/A | Competitive |

**Conclusions:**
- Opus slightly better than Gemini overall
- META Prompt improves output across models
- Canvas/artifact mode degrades code quality (no canvas > canvas)
- After Claude 4.5, Opus clearly outperforms Gemini Pro 3.0

## When to Use This

- Evaluating which LLM to use for code generation tasks
- Comparing prompting strategies (META prompt vs. bare)
- Studying the effect of artifact/canvas mode on code quality
- Benchmarking new models against established baselines

## Project Structure

```
├── input_prompt.txt                          # Standardized test prompt (Chinese)
├── claude_opus4.py                           # Claude Opus 4 output
├── claude_opus4_no_prompt.py                 # Opus 4, no META prompt
├── claude_opus4_no_prompt_no_artifact.py     # Opus 4, no prompt, no artifact
├── claude_opus_4.5_METAPrompt.py             # Opus 4.5 with META prompt
├── claude_sonnet_4.py                        # Sonnet 4 output
├── gemini2.5pro_canvas.py                    # Gemini 2.5 Pro with canvas
├── gemini2.5pro_no_canvas.py                 # Gemini 2.5 Pro without canvas
├── gemini_3.0_pro_METAprompt_no_canvas.py    # Gemini 3.0 Pro with META prompt
├── deepseekR1.py                             # DeepSeek R1 output
├── grok4.py                                  # Grok 4 output
└── main.py                                   # Entry point
```

## Run the Benchmark

```bash
# Install dependencies
pip install pygame

# Run any model's output
python claude_opus_4.5_METAPrompt.py
# → 800x800 window with bouncing balls in rotating heptagon
```


## Related Projects

| Project | What It Does |
|---------|-------------|
| [WitMani Game Animator](https://github.com/sephirxth/WitMani-game-animator) | AI-powered game sprite animation — practical application of LLM + image generation |
| [OpenClaw Canvas](https://github.com/sephirxth/openclaw-canvas) | AI agent orchestration dashboard — built on the same multi-model philosophy |
| [SurvivorDemo](https://github.com/sephirxth/SurvivorDemo) | Browser survival game — one of the target outputs these LLMs would generate |
| [NetOps](https://github.com/sephirxth/transport-sim) | Network routing puzzle game — another complex codebase for LLM evaluation |

[All projects →](https://github.com/sephirxth)

## License

MIT
