### Configuration keys

 * `llm.model` — LLM model name passed to litellm. Some useful llm.model values:
   * `together_ai/Qwen/Qwen3.5-9B` - good value ($0.10/$0.15 per 1M tokens)
     * doesn't support tool use, needed for pydantic-ai models
   * `together_ai/google/gemma-3n-E4B-it` - ultra-cheap ($0.02/$0.04 per 1M tokens)
     * doesn't support tool use, needed for pydantic-ai models
   * `claude-haiku-4-5-20251001` - quick cheap and stable, needs Anthropic API key
   * `together_ai/deepseek-ai/DeepSeek-V3.1` - cheap but strong reasoning ($0.60/$1.70 per 1M tokens)
   * `together_ai/openai/gpt-oss-20b` - very cheap ($0.05/$0.20 per 1M tokens)
   * `together_ai/openai/gpt-oss-120b` - good value, larger ($0.15/$0.60 per 1M tokens)
   * `together_ai/Qwen/Qwen3-Next-80B-A3B-Instruct` - good value, MoE ($0.15/$1.50 per 1M tokens)
   * `gemini/gemini-2.5-flash` - thinking model ($0.30/$2.50 per 1M tokens, 65K output)
   * `gemini/gemini-2.5-flash-lite` - cheap Gemini ($0.10/$0.40 per 1M tokens, 65K output)
   * `gemini/gemini-3.1-flash-lite-preview` - ultra-cheap Gemini preview ($0.25/$1.50 per 1M tokens, 65K output)
 * `llm.thinking` — if truthy, include `<thought>` scaffolding in simulate prompts
 * `llm.reasoning_effort` — for Gemini thinking models: low/medium/high
 * `simulate.full_src` — if truthy, keep the full function body in Interface.src; otherwise strip to signature + docstring
 * `echo.model` — print which model is being called
 * `echo.llm_input` — print the prompt sent to the LLM in a box
 * `echo.llm_output` — print the LLM response in a box
 * `echo.code_eval_output` — print result of executing LLM-generated code
 * `echo.service` — print service information
 * `echo.call` — print function call signatures
 * `echo.box_width` — max width for terminal debug boxes printed by `echo_boxed()`. If `0` (default) the width is auto-detected from the terminal (`shutil.get_terminal_size`, fallback 120 columns), minus the box frame. Long lines wrap; existing newlines are preserved.
 * `dataset.json_data_dir` — directory containing dataset JSON files (default `data`)
 * `dataset.ptools_module` — Python module to import for ptools (default `ptools`)
 * `evaluate.expt_name` — name tag for the experiment (used in result filenames and dataframes)
 * `evaluate.root_interface` — default top-level interface as `module.name` (used when `--interface` is omitted)
 * `evaluate.result_dir` — directory to save results CSV and config YAML snapshot
 * `evaluate.record_details` — if `True`, include full rollout recordings in JSONL output (default `False`)
 * `evaluate.max_workers` — number of parallel evaluation threads (default 1)
 * `pydantic.retries` — max output-validation retries for pydantic-ai Agent (default 1)
 * `cachier.enable_caching` — if `False`, bypass cachier entirely (default `True`)
 * `cachier.cache_dir` — directory for cachier's on-disk cache
 * Other `cachier.*` keys are passed through to `@cachier()` (e.g. `stale_after`, `allow_none`)
