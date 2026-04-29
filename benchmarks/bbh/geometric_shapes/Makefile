#
# Run experiments - all on the validation data
#

EXPT = uv run python -m secretagent.cli.expt
INTERFACE = --interface ptools.identify_shape
EVALUATOR = --evaluator ptools.GeometricShapesEvaluator
DOTPAIRS ?=

basics: unstructured_baseline structured_baseline workflow pot react

# the hand-coded workflow
workflow:
	$(EXPT) run $(INTERFACE) $(EVALUATOR) evaluate.expt_name=workflow $(DOTPAIRS) \
	  ptools.identify_shape.method=direct \
	  ptools.identify_shape.fn=ptools.geometric_shapes_workflow

# zero-shot structured queries
structured_baseline:
	$(EXPT) run $(INTERFACE) $(EVALUATOR) evaluate.expt_name=structured_baseline $(DOTPAIRS) \
	  ptools.identify_shape.method=simulate

# zero-shot unstructured queries with a vanilla prompt
unstructured_baseline:
	$(EXPT) run $(INTERFACE) $(EVALUATOR) evaluate.expt_name=unstructured_baseline $(DOTPAIRS) \
	  ptools.identify_shape.method=direct \
	  ptools.identify_shape.fn=ptools.zeroshot_unstructured_workflow

# program of thought
pot:
	$(EXPT) run $(INTERFACE) $(EVALUATOR) evaluate.expt_name=pot $(DOTPAIRS) \
	  ptools.identify_shape.method=program_of_thought \
	  ptools.identify_shape.tools=[ptools.extract_path_and_options,ptools.decompose_path,ptools.describe_command,ptools.compute_angle,ptools.describe_shape,ptools.select_option]

# ReAct using simulate_pydantic (which runs ReAct if there are tools),
# wrapped with extract_option_letter so the final output is the bare letter.
react:
	$(EXPT) run $(INTERFACE) $(EVALUATOR) evaluate.expt_name=react $(DOTPAIRS) \
	  ptools.identify_shape.method=direct \
	  ptools.identify_shape.fn=ptools.geometric_shapes_react_workflow \
	  ptools.react_identify_shape.method=simulate_pydantic \
	  ptools.react_identify_shape.tools=[ptools.extract_path_and_options,ptools.decompose_path,ptools.describe_command,ptools.compute_angle,ptools.describe_shape,ptools.select_option]

# quick test of react on a single example
quick-test-react:
	$(EXPT) quick-test $(INTERFACE) \
	  ptools.identify_shape.method=direct \
	  ptools.identify_shape.fn=ptools.geometric_shapes_react_workflow \
	  ptools.react_identify_shape.method=simulate_pydantic \
	  ptools.react_identify_shape.tools=[ptools.extract_path_and_options,ptools.decompose_path,ptools.describe_command,ptools.compute_angle,ptools.describe_shape,ptools.select_option] --example valid.006

# quick test on a single example
quick-test:
	$(EXPT) quick-test $(INTERFACE) --example valid.013 \
	  ptools.identify_shape.method=direct \
	  ptools.identify_shape.fn=ptools.geometric_shapes_workflow

# cached test of react on a single example (LLM cache stays active)
cached-test-react:
	$(EXPT) cached-test $(INTERFACE) \
	  ptools.identify_shape.method=direct \
	  ptools.identify_shape.fn=ptools.geometric_shapes_react_workflow \
	  ptools.react_identify_shape.method=simulate_pydantic \
	  ptools.react_identify_shape.tools=[ptools.extract_path_and_options,ptools.decompose_path,ptools.describe_command,ptools.compute_angle,ptools.describe_shape,ptools.select_option] --example valid.006

# cached test on a single example (LLM cache stays active)
cached-test:
	$(EXPT) cached-test $(INTERFACE) --example valid.013 \
	  ptools.identify_shape.method=direct \
	  ptools.identify_shape.fn=ptools.geometric_shapes_workflow

#
# View results of past experiments
#

list:
	uv run python -m secretagent.cli.results list results/*

avg:
	uv run python -m secretagent.cli.results average --metric correct --metric cost results/*

pair:
	uv run python -m secretagent.cli.results pair --metric correct --metric cost results/*

compare:
	uv run python -m secretagent.cli.results compare-configs results/*

costs:
	uv run python -m secretagent.cli.costs llm_cache
