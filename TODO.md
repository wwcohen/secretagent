Next steps

 * for cachier version of pydantic agents
   * caching fails because you can't pickled BaseModels that are undefined
   * need to sort out the caching strategy
     * cachier's globals are not working like I think they should!
	 * maybe have config's cache.cache_dir, cache.skip --> cachier__skip_cache=True, cache.reset=True
	 * pydantic_impl and llm_util have reset_cache functions 
     * cachier docs are NOT up-to-date...
 * in benchmarks/sports_understanding/
   * write conf - data loaders and implementations
     * zero shot prompt_llm
     * zero shot simulate
     * workflow with ptools
     * react with ptools
 * then look at code generation from react pipelines
