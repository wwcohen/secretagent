"""A demo of secretagent
"""

import logging
import pprint

#
# Define some routines with Pythonic interfaces that are will be
# implemented with an LLM.  All you need to do with these routines is
# give return types and doc strings. Optionally they can be given
# local configurations.
#

import secretagent as sec

@sec.subagent()
def analyze_sentence(sentence: str) -> (str, str, str):
  """Extract a names of a player, and action, and an optional event.

  The action should be as descriptive as possible.  The event will be
  an empty string if no event is mentioned in the sentence.

  Examples:
  >>> analyze_sentence("Bam Adebayo scored a reverse layup in the Western Conference Finals.")
  ('Bam Adebayo', 'scored a reverse layup', 'in the Western Conference Finals.')
  >>> sports_understanding('Santi Cazorla scored a touchdown.')
  ('Santi Cazorla', 'scored a touchdown.', '')
  """

@sec.subagent()
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
    
@sec.subagent()
def consistent_sports(sport1: str, sport2: str) -> bool:
  """Compare two descriptions of sports, and determine if they are consistent.

  Descriptions are consistent if they are the same, or if one is more
  general than the other.
  """
  ...

#
# Now these subagents can be called as if they were implemented in Python.
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

if __name__ == '__main__':

  # configure the service and model used by default
  sec.configure(service="anthropic", model="claude-haiku-4-5-20251001")

  # this context will push some more things into the configuration and
  # remove them when we exit - in this case echo the service used
  # and the subagent inputs/outputs
  with sec.configuration(echo_call=True, echo_service=True):
    result = sports_understanding_workflow("Tim Duncan scored from inside the paint.")

  # this context records all the subagent calls in a list of dicts
  with sec.recorder() as rollout:
    result = sports_understanding_workflow("DeMar DeRozan was called for the goal tend.")
    pprint.pprint(rollout)
