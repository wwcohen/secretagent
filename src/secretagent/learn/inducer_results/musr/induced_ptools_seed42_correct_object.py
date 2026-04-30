"""Induced ptools for MUSR object (seed=42).

Auto-generated from results/20260411.032029.object_react_train_seed42/results.jsonl.
Model: together_ai/deepseek-ai/DeepSeek-V3.
Do not edit — regenerate via generate_induced_configs.py.
"""

from secretagent.core import implement_via
from ptools.ptools_common import _REACT_STATE


@implement_via('simulate')
def _formulate_search_query_impl(narrative: str, focus: str) -> str:
    """
    This function analyzes a narrative and a focus area to generate a precise search query for finding relevant information.
    It extracts key entities (people, objects, locations) and actions from the focus string to construct a query that will help
    locate narrative segments related to the specific aspect of interest. The agent should pay attention to:
    - Identifying the main subject (who) and object (what) from the focus phrase
    - Including relevant actions (e.g., 'took', 'moved', 'placed', 'found')
    - Considering time references if relevant to the focus
    - Using quotation marks for exact phrase matching when appropriate
    - Theory-of-mind considerations: the query should target information about character knowledge/beliefs when relevant

    Returns:
    A structured string in the format: "SEARCH: [query]" where [query] is the formulated search phrase.

    Example return: "SEARCH: 'Richie took saxophone'"
    """


def formulate_search_query(focus: str) -> str:
    """Creates a targeted search query to find specific information within a narrative.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _formulate_search_query_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _analyze_character_knowledge_impl(narrative: str, focus: str) -> str:
    """
    Analyzes a narrative to determine what a specific character knows or believes about an object's location, considering their presence during events, observations, and any information they may have received.

    This function examines:
    - When the character was present/absent during object movements
    - What the character directly observed about the object
    - What information the character may have received from others
    - Whether the character has searched for or used the object
    - Time-sensitive information that might affect their knowledge

    The response should be structured as:
    - Character: [character name]
    - Object: [object name]
    - Known locations: [list of locations character knows about]
    - Last known location: [last location character was aware of]
    - Knowledge gaps: [any missing information or uncertainties]
    - Reasoning: [brief explanation of the analysis]

    Pay special attention to:
    - Theory of mind: what the character actually knows vs. true location
    - Character absence during critical events
    - Visual/tactile limitations (e.g., not seeing inside containers)
    - Time decay of information (if relevant)
    - Contradictory information the character may have received

    Returns:
    A structured string analysis of the character's knowledge state.

    Example return:
    \"\"\"
    Character: John
    Object: baton
    Known locations: Fred's pocket, drawer
    Last known location: Fred's pocket
    Knowledge gaps: Unaware of Mary taking baton from drawer
    Reasoning: John saw baton in Fred's pocket but was absent when Mary moved it
    \"\"\"
    """


def analyze_character_knowledge(focus: str) -> str:
    """Determines what a specific character knows or believes about an object's location based on narrative events and observations.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _analyze_character_knowledge_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _extract_belief_location_impl(narrative: str, focus: str) -> str:
    """
    Extracts information from the narrative to determine where a target character believes a specific object is located, considering theory of mind where beliefs may differ from reality.

    This function analyzes the narrative to track:
    - The actual movement history of the object
    - What the target character observed or was informed about
    - Whether the character's knowledge might be outdated due to absence or deception
    - Key events that would update the character's mental model

    Response should be structured as a JSON-shaped string containing:
    - character: name of the target character
    - object: name of the object being tracked
    - believed_location: where the character believes the object is
    - reasoning: brief explanation of why this belief is held
    - confidence: high/medium/low based on narrative clarity

    Pay special attention to:
    - Characters leaving/returning and what they witnessed
    - Explicit statements about character knowledge or belief
    - Deceptive actions or false information provided
    - Time sequences and whether characters were present for key events
    - Whether the narrative provides direct evidence of belief or requires inference

    Returns:
    A string in JSON format like: {"character": "Rinchen", "object": "necklace", "believed_location": "temple", "reasoning": "Rinchen saw the necklace in the temple and never witnessed its removal", "confidence": "high"}
    """


def extract_belief_location(focus: str) -> str:
    """Determines where a specific character believes an object is located based on the narrative and their knowledge.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _extract_belief_location_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _infer_character_belief_impl(narrative: str, focus: str) -> str:
    """
    Extracts information about character knowledge, object movements, and temporal sequence from a narrative.
    Analyzes what a specific character knows about object locations based on:
    - What they directly observed
    - When they were present/absent during movements
    - Information they may have received from others
    - The character's role or expertise with objects

    Pay special attention to:
    - Timing of character arrivals/departures relative to object movements
    - Explicit statements about character knowledge or awareness
    - Temporary vs. permanent object locations
    - Whether the character could have learned about movements indirectly

    Returns: A JSON string with belief_location (where character thinks object is) 
    and reasoning (step-by-step explanation of the inference).

    Example return:
    {
      "belief_location": "bookshelf",
      "reasoning": "Character was present when object was placed on bookshelf but absent when it was moved to table. No evidence suggests they learned about the move."
    }
    """


def infer_character_belief(focus: str) -> str:
    """Analyzes narrative text to determine where a specific character believes an object is located based on their knowledge and observations.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _infer_character_belief_impl(_REACT_STATE["narrative"], focus)


@implement_via('simulate')
def _track_object_movement_timeline_impl(narrative: str, focus: str) -> str:
    """
    Reconstructs the complete timeline of an object's movement through locations and characters' interactions with it.

    Extracts:
    - All instances of object movement/placement with timestamps or sequence indicators
    - Which characters were present/witnessed each movement
    - Character comings and goings relative to movement events
    - Explicit mentions of character knowledge or beliefs

    Response structure should be a chronological list of events with:
    - Event description
    - Characters involved
    - Location changes
    - Visibility/witness information
    - Time/sequence indicators

    Pay attention to:
    - Theory of mind: distinguish actual location from character beliefs
    - Character absence: if character left before movement, they won't know subsequent moves
    - Explicit knowledge statements: characters may state what they know/believe
    - Temporal ambiguity: watch for vague time references that need disambiguation
    - Multiple object instances: ensure tracking the correct specific object

    Returns:
    A structured timeline string with chronological events, for example:
    \"Timeline for saxophone:
    1. Initial location: storage box (known to all)
    2. Oliver moves saxophone to stage (Oliver witnesses, Richie absent)
    3. Richie moves saxophone to green room (Richie witnesses, Oliver absent)
    4. Oliver returns, saxophone remains in green room (Oliver unaware of move)\"
    """


def track_object_movement_timeline(focus: str) -> str:
    """Analyzes narrative to reconstruct object movement timeline and determine character beliefs about object location.

    Args:
        focus: what aspect to reason about (e.g. a suspect, a
               time window, a belief state).
    """
    return _track_object_movement_timeline_impl(_REACT_STATE["narrative"], focus)
