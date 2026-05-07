"""Another simple demo of secretagent based on the
'sports_understanding' task in the BIG Bench Hard benchmark.

This demonstrates the 'Program of Thoughts' implementation, and also
makes more use of structured inputs/outputs.
"""


from secretagent import config, record
from secretagent.core import implement_via

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

@implement_via('program_of_thought')
def are_sports_in_sentence_consistent(sentence: str) -> bool:
  """An agent that uses the subagents defined above, in some order
  that it determines on a case-by-case bases.
  """

if __name__ == '__main__':

    # Echo a bunch of things, including the generated code.
    # If you want to use caching with structured objects
    # it's best to not use the default cache.
    config.configure(
        llm={'model': "claude-haiku-4-5-20251001"}, 
        echo={'llm_input': True, 'llm_output': True, 
              'code_eval_input': True, 'code_eval_output': True},
        cachier={'enable_caching': False, 'cache_dir': '/tmp/su_pyd.d'})

    with record.recorder() as rollout:
        result = are_sports_in_sentence_consistent("Tim Duncan scored from inside the paint.")
        print('result is', result)
        pprint.pprint(rollout)

    # Find the generated code
    print(' generated code '.center(60, '-'))    
    for step in rollout:
        if 'step_info' not in step:
            continue
        if 'generated_code' not in step['step_info']:
            continue
        print(step['step_info']['generated_code'])
    print(' result '.center(60, '-'))    
    print(result)
