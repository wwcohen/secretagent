"""A demo of secretagent
"""

import logging
import pprint

import secretagent as sec

@sec.subagent(echo=True)
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

@sec.subagent(echo=True)
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
    
@sec.subagent(echo=True)
def consistent_sports(sport1: str, sport2: str) -> bool:
  """Compare two descriptions of sports, and determine if they are consistent.

  Descriptions are consistent if they are the same, or if one is more
  general than the other.
  """
  ...

def sports_understanding_workflow(sentence):
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
  sec.configure(service="anthropic", model="claude-3-haiku-20240307")
  sports_understanding_workflow("DeMar DeRozan was called for the goal tend.")

    
