Next steps

 * Clean up the results and save_file stuff
   * save_file should drop get_files and add filter_paths(list[Path]) -> list([Path])
	 * filter_files takes args latest=k, dot_list_to_check
     * cli/results.py commands take list of files as command-line extra args plus filter_files options
 * Check about disabling caching from the command-line
 * Rework the results.py thing
   * Figure out how to specify things to pair
 * Run experiments in sports_understanding
   * Fix problems with pydantic react factory configuration
   * Make tool use consistent between PoT and pydantic factories
   * Debug the most-recent issue: should only be the most recent 
     file for each tag
   * write conf - data loaders and implementations
     * zero shot prompt_llm
     * zero shot simulate
     * workflow with ptools
     * react with ptools
     * use smaller models till the task gets "interesting"

