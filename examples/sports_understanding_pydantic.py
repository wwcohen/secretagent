"""A demo of secretagent, based on the 'sports_understanding' task in
BBH.
"""

from secretagent import config, record
from secretagent.core import interface, implement_via

from pydantic import BaseModel
import pprint

class StructuredSportsSentence(BaseModel):
    player: str
    action: str
    event: str | None

class SportsInSentence(BaseModel):
    player_sport: str
    action_sport: str
    event_sport: str | None

@implement_via('simulate_pydantic')
def analyze_sentence(sentence: str) -> StructuredSportsSentence:
  """Extract a names of a player, and action, and an optional event.

  The action should be as descriptive as possible.  The event will be
  None if no event is mentioned in the sentence.
  """

@implement_via('simulate_pydantic')
def find_sports(sentence: StructuredSportsSentence) -> SportsInSentence:
  """Find the sports that are most commonly associated with the
  player, action, and event.  If any of these is None then the
  corresponding sport will be none.
  """

@implement_via('simulate_pydantic')
def consistent(sports: SportsInSentence) -> bool:
  """Decide if all the non-None sports are consistent with each other.

  Sport strings are consistent if they are the same, or if one is more
  general than the other.
  """


#
# Now these subagents can be called as if they were implemented in Python.
#

def sports_understanding_workflow(sentence):
  """A workflow that uses the subagents defined above.
  """
  return consistent(find_sports(analyze_sentence(sentence)))

@interface
def are_sports_in_sentence_consistent(sentence: str) -> bool:
  """An agent that uses the subagents defined above.
  """

if __name__ == '__main__':

    config.configure(
        llm={'model': "claude-haiku-4-5-20251001"}, 
        echo={'llm_input': True, 'llm_output': True},
        cachier={'enable_caching':True, 'cache_dir':'/tmp/su_pyd.d'})

    # or could use tools=[analyze_sentence, find_sports, consistent]
    are_sports_in_sentence_consistent.implement_via(
        'simulate_pydantic', tools='__all__')

    with record.recorder() as rollout:
        result = are_sports_in_sentence_consistent("Tim Duncan scored from inside the paint.")
        print('result is', result)
        pprint.pprint(rollout)


