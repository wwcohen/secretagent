Next steps

 * Refactor expt.py
   * move tool configuration to core.py? or core_impl?
   * clean up Evaluator/measure? maybe abstract is compare outputs expected, predicted?? 
   * write conf - data loaders and implementations
     * zero shot prompt_llm
     * zero shot simulate
     * workflow with ptools
     * react with ptools
 * move over old result cli methods to soemwhere in src/secretagent --- analyze?
 * then look at code generation from react pipelines
 * rename core_impl and pydantic_impl to impl_core/impl_pydantic?

----------

 * interface.impl: dict[str, Callable]          # stores possible implementations
 * def ptool.plan_runner(**cfg) -> Callable # build Workflow and execute
 * def ptool.vibe_coded(**cfg) -> Callable  # return python implementation
 * def ptool.distill_traces(Agent | Planner, train, **cfg) -> Callable  # distill agent

 # add new ptools ...
 * def ptool.distill_thoughts(Agent | Planner, train, **cfg) -> Callable  # distill agent
 * def ptool.generalize_annotations(train, **cfg) -> Callable  # distill agent
   * also extends the set of tools

 * optimization strategy - black-box optimization
   * pick from current configs
   * based on profile, look at bottlenecks and expand implementations
     * to improve quality: stronger models, think, agentify
     * to improve speed: distill, vibe_code

