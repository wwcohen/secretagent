"""Another simple demo of secretagent, based on the
'sports_understanding' task in the BIG Bench Hard benchmark.
"""

from secretagent import config, record
from secretagent.core import interface
import pprint

#
# Define some simple Interfaces - these look like Python functions but
# are not implemented (yet)
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

#
# The interfaces can be called in code just like Python.
#

def sports_understanding_workflow(sentence):
  """A workflow that uses the subagents defined above.
  """
  player, action, event = analyze_sentence(sentence)
  player_sport = sport_for(player)
  action_sport = sport_for(action)
  result = consistent_sports(player_sport, action_sport)
  if event:
    event_sport = sport_for(event)
    result = result and consistent_sports(player_sport, event_sport)
  print(f'Final answer: {"yes" if result else "no"}')
  return result


# make the output a little prettier
def _print_section_head(tag: str):
  print(f' {tag} '.center(60, '-'))

#
# A main that demonstrates how to use Interfaces
#

if __name__ == '__main__':

  # Configure the model used by default - any liteLLM model is ok,
  # as long as you have API keys set up!
  config.configure(llm={'model': "claude-haiku-4-5-20251001"})

  # One way to implement an interface is to 'simulate' it using an
  # LLM. This code binds the interfaces above to that implementation
  # strategy.

  analyze_sentence.implement_via('simulate')
  sport_for.implement_via('simulate')
  consistent_sports.implement_via('simulate')

  _print_section_head('workflow with simulated interfaces')
  result = sports_understanding_workflow("Tim Duncan scored from inside the paint.")
  print('Result is', result)

  # This context manager will push some more things into the
  # configuration and remove them when we exit.  In this case we
  # config request to trace some actions.
  with config.configuration(
      echo={'service': True, 'llm_input': True, 'llm_output': True, 'box_width':120},
      cachier={'enable_caching': False}):
    result = sports_understanding_workflow("Tim Duncan scored from inside the paint.")
    print('Traced result is', result)

  # You can get back more information using this context manager
  _print_section_head('recording the same workflow')
  with record.recorder() as rollout:
    result = sports_understanding_workflow("DeMar DeRozan was called for the goal tend.")
    pprint.pprint(rollout)
