Next steps

 * check that the smoke tests in the main of core.py are represented
   in tests/test_core.py, and once they are, remove them from core
 * add a register_factory method to core.py and use that in pydantic_impl
   instead of importing _FACTORIES
 * move the DirectFactory, EchoFactory, SimulateFactory out of core.py
   into a new core_impl.py
 * add a new PromptLLMFactory which is similar to SimulateFactory but
   instead of create_prompt/parse_output methods, allows the user to
   supply a prompt template and parse_output strategies as arguments
   given to the factory:
   *  prompt_template_str  / prompt_template_file (both strings, throw
   an error unless exactly one is given)
   *  answer_pattern
      * defaults to '<answer>(.*)</answer>'
      * if not given and return type is 'str' (or not specified) then
        return the full answer.
 
