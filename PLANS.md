Status

 * Pydantic agents with tool use now seem to be working, and are recorded
   * The messages they produce are messy
   * Record should boil this down somehow

Proposal

 * build out over Pydantic AI, Hydra
   * how?
	 * configuration wraps hydra
	 * recorder uses pydantic ai data structures for compatibily with agents
     * ptool decorator is based on existing wrapper but ...
	   * wrapper currently sees func and args and returns a function that implements llm_call
	   * revised wrapper
		   * side effect is to add func (as a ptoolspec) to a registry
		   * returned wrapper will lookup func in the registry and select an implementation to run
		   * caching, backoffs are compound implementations
   * why?
	 * pydantic agents can report message sequences, including tool calls
		 * you can audit message sequences (!)
	 * they can return and accept Pydantic models 
	 * basic agent types (react etc) are implemented
	 * pydantic_evals have Dataset, Case, ... 
	 * there is cost tracking - via logfire
	 * there are built-in code execution tools

Packages to evaluate

 * litellm - llm interface - seems fine!
 * instructor - structured output llm client (do I need this pydantic backend)
 * pydantic_evals

Next steps
 * Sort out configs to use hydra
 * Build out evals for sports_understanding example
   * check in json data
   * load train/valid/test splits, maybe 80/80/80?
   * set up pydantic evals for accuracy and cost with multiple configs
     * baseline prompt
     * baseline structured prompt
     * agentic tool calling
       * sort out how to configure/save tool examples
     * k-shot PoT + execute planning
	 * fixed workflow tool calling
 * Test distillation approaches
   * Agent plans -> Workflow

Ideas:
 *  distillation of ptool as a decision tree learning task

 * what's new: ptool (an interface)

   @ptool
   def fun(....): 

 * ptool.impl: dict[str, Callable]          # stores possible implementations
 * def ptool.llm_call(**cfg) -> Callable    # return llm*calling implementation
 * def ptool.react_agent(**cfg) -> Callable # return agentic implementation
 * def ptool.plan_runner(**cfg) -> Callable # build Workflow and execute
 * def ptool.vibe_coded(**cfg) -> Callable  # return python implementation
 * def ptool.distill_traces(Agent | Planner, train, **cfg) -> Callable  # distill agent

 # add new ptools ...
 * def ptool.distill_thoughts(Agent | Planner, train, **cfg) -> Callable  # distill agent
 * def ptool.generalize_annotations(train, **cfg) -> Callable  # distill agent
   * also extends the set of tools

 * global ptool config:
   * for each ptool.implementation name
      * local config
	  * training examples
      * serializable implementation
      * metrics by dataset

 * optimization strategy - black-box optimization
   * pick from current configs
   * based on profile, look at bottlenecks and expand implementations
     * to improve quality: stronger models, think, agentify
     * to improve speed: distill, vibe_code

