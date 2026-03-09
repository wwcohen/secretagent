Next steps

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
 
