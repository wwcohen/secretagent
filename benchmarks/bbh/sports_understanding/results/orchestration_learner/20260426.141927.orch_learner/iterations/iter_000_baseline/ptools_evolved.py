"""A demo of secretagent, based on the 'sports_understanding' task in
BBH.

Backstory: These tools were derived from the program trace prompt
'mock' for sports_understanding in
https://github.com/wwcohen/doctest-prompting.

"""

from secretagent.core import interface, implement_via

#
# tools
#

@interface
def analyze_sentence(sentence: str) -> tuple[str, str, str]:
  """Extract a names of a player, and action, and an optional event.

  The action should be as descriptive as possible.  The event will be
  an empty string if no event is mentioned in the sentence.

  Examples:
  >>> analyze_sentence("Bam Adebayo scored a reverse layup in the Western Conference Finals.")
  ('Bam Adebayo', 'scored a reverse layup', 'in the Western Conference Finals.')
  >>> sports_understanding('Santi Cazorla scored a touchdown.')
  ('Santi Cazorla', 'scored a touchdown.', '')
  """

@interface
def sport_for(x: str)-> str:
  """Return the name of the sport associated with a player, action, or event.

  Examples:
  >>> sport_for('Bam Adebayo')
  'basketball'
  >>> sport_for('scored a reverse layup')
  'basketball'
  >>> sport_for('in the Western Conference Finals.')
  'basketball'
  >>> sport_for('Santi Cazorla')
  'soccer'
  >>> sport_for('scored a touchdown.')
  'American football and rugby'
  """
    
@interface
def consistent_sports(sport1: str, sport2: str) -> bool:
  """Compare two descriptions of sports, and determine if they are consistent.

  Descriptions are consistent if they are the same, or if one is more
  general than the other.
  """
  ...

@interface
def are_sports_in_sentence_consistent(sentence:str) -> bool:
  """Determine plausibility of a sports-related sentence.

  Specifically, determine if the sports associated with the player,
  action and event in a sentence are all consistent with each other.
  """
  ...

def sports_understanding_workflow(sentence:str) -> bool:
  """Handcoded workflow for are_sports_in_sentence_consistent.
  """
  player, action, event = analyze_sentence(sentence)
  player_sport = sport_for(player)
  action_sport = sport_for(action)
  result = consistent_sports(player_sport, action_sport)
  if event:
    event_sport = sport_for(event)
    result = result and consistent_sports(player_sport, event_sport)
  return result

#
# zeroshot unstructured model is a workflow - first get a string
# answer, then use a second tool to generate a bool from that
#

@implement_via('prompt_llm', prompt_template_file='prompt_templates/zeroshot.txt')
def zeroshot_are_sports_in_sentence_consistent(sentence: str) -> str:
  ...

@implement_via('simulate')
def convert_llm_output_to_true_or_false(llm_output: str) -> bool:
  """Given an llm's output, approximate the intended answer as bool.
  """
  ...

def zeroshot_unstructured_workflow(sentence:str) -> bool:
  """Workflow for using a zero-shot prompt and coercing the type to bool.

  To run the zeroshot unstructured model, bind this to the
  implementation of 'are_sports_in_sentence_consistent'.
  """
  llm_output = zeroshot_are_sports_in_sentence_consistent(sentence)
  return convert_llm_output_to_true_or_false(llm_output)
