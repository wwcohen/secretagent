"""Interfaces for MUSR object placement (theory of mind)."""

from secretagent.core import interface
from ptools_common import (  # noqa: F401  (re-export so the loaded ptools module exposes them)
    raw_answer,
    extract_index,
    react_solve,
)


@interface
def extract_movements(narrative: str) -> str:
    """Extract a chronological list of every object-movement event in the narrative.

    For each move event, record:
    - object: which object is being moved
    - from_location: where it was before the move
    - to_location: where it ends up after the move
    - actor: who performed the move (the mover)
    - present: list of OTHER characters who were in the scene and witnessed the move
    - absent: list of characters who are mentioned in the story but were NOT in the scene
      when this move happened (and therefore did not witness it)

    Be exhaustive — include EVERY move of EVERY object, in the order they
    happen in the narrative. Do not paraphrase locations: use the exact
    place names that appear in the story so they match the answer choices
    later. Do not infer moves that are not described.

    Format the output as a numbered list:
        1. object=<X>, from=<L1>, to=<L2>, actor=<A>, present=[...], absent=[...]
        2. object=<Y>, from=<L1>, to=<L3>, actor=<B>, present=[...], absent=[...]
        ...

    This list is the load-bearing structure for false-belief reasoning, so
    accuracy of who-was-present-when matters more than prose quality.
    """


@interface
def extract_discoveries(narrative: str) -> str:
    """Extract incidental discoveries from the narrative.

    A "discovery" is a moment where a character notices/sees/learns the
    location of an object WITHOUT witnessing the move that put it there.
    These update a character's belief about the object's location even
    though they were not present when it was moved.

    Examples of discoveries:
    - "Bob walked past the kitchen and saw the keys on the counter."
    - "Alice looked into the box and noticed the necklace inside."
    - "Tom told Sarah that the wrench was in the toolshed."  (verbal report
      counts as a discovery — Sarah now believes that)

    For each discovery, record:
    - observer: the character who learned the location
    - object: which object they learned about
    - location: where they observed/were-told the object is
    - mode: 'saw_directly' | 'told_by_<name>' | 'inferred_from_<event>'

    Format as a numbered list:
        1. observer=<X>, object=<O>, location=<L>, mode=<M>
        2. ...

    If there are no incidental discoveries, return: "No discoveries."
    Be conservative — only include events explicitly stated in the narrative.
    """


@interface
def infer_belief(narrative: str, movements: str, question: str, choices: list) -> str:
    """Determine where the target person believes the target object is located.

    You receive:
    1. The FULL original narrative (re-read it for details extraction may have missed)
    2. Extracted object movements with presence/absence info
    3. Incidental discoveries (someone saw/noticed an object without witnessing the move)
    4. The question identifying the target person and object, and answer choices

    Your task — determine the person's BELIEF about the object's location:

    Step 1: Start with the object's initial location (everyone knows this)
    Step 2: For each movement of the target_object (in chronological order):
       - If target_person is in "present" → they know the new location
       - If target_person is in "absent" → they still believe the old location
    Step 3: Check discoveries — if target_person discovered the target_object
       at a location, that UPDATES their belief to that location
    Step 4: Re-read the narrative to check for anything the extraction missed:
       - Did someone TELL the target person where the object is?
       - Did the target person GO TO the object's location and see it there?
       - Did the target person interact with something NEAR the object?
    Step 5: Match the believed location to one of the answer choices

    IMPORTANT: The question asks where the person would LOOK, which means
    where they BELIEVE the object is — not necessarily where it actually is.
    """


@interface
def answer_question(narrative: str, question: str, choices: list) -> int:
    """Read the narrative and answer where someone would look for an object.
    This is a theory-of-mind task: the answer is based on what the person
    believes, not the object's actual location.
    Return the 0-based index of the correct choice.
    """
    text = raw_answer(narrative, question, choices)
    return extract_index(text, choices)


@interface
def answer_question_workflow(narrative: str, question: str, choices: list) -> int:
    """Solve by extracting movements + discoveries, inferring belief, then matching.

    4-step hand-designed workflow:
      1. extract_movements — chronological list of who-saw-which-move
      2. extract_discoveries — incidental observations of object locations
      3. infer_belief — combine narrative + movements + discoveries to
         determine the target person's belief about the target object
      4. extract_index — match the inferred belief to one of the choices
    """
    movements = extract_movements(narrative)
    discoveries = extract_discoveries(narrative)
    combined = (
        f"## Object movements\n{movements}\n\n"
        f"## Incidental discoveries\n{discoveries}"
    )
    text = infer_belief(narrative, combined, question, choices)
    return extract_index(text, choices)
