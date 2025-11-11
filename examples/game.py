"""Todo:

game builder 
 - programatically add some paths and mazes
 - move room description gen to world builder, with a game-specific
prompt, and programatic choice of a nearby room.  make room
generations discuss the exits.
 - bullwhip puzzle
 - feather-guided maze in a cavern?
   (4x4 grid, add random edges until corners connect)

game
 - add hints
 - n_th_review(n, description)

"""

from cachier import cachier
from functools import partial
import random

from pydantic import BaseModel, Field
from textwrap import dedent, fill, wrap
from typing import Callable

import secretagent as sec


# LLM access
#

@sec.subagent()
def refusal(
        command: str, 
        room_description: str, 
        valid_directions: list[str],
        player_inv: list[str],
        room_inv: list[str]) -> str:
    """Explain why a command is not applicable here.

    Inputs:
      command: the inapplicable command issued by the player
      room_description: a description of the current room
      valid_directions: a list of directions that can be traveled
      player_inv: a list of the items carried by the player.
      room_inv: a list of the items in the room.

    Output:
      An explanation as to why the command is invalid.

    Some examples:

    >>> refusal("go south", "You are in a vast desert with an old pyramid just north of you", ['north'], [], [])
    "The desert is much too hostile to explore without the proper equipment."
    
    >>> refusal("examine whip", "You are in the entrance to a dark tunnel", ['north'], ["fedora", "gun"], [])
    "You don't see anything like that here."

    >>> refusal("talk to the mummy", "You are in a burial chamber.", ['south', 'west'], [], [])
    "It seems unlikely that the mummy will answer, since it has been dead for a while."
    """

@cachier()
@sec.subagent()
def normalize_command(user_command: str, possible_commands: tuple[str]) -> str:
    """Given a user command, find a possible command that matches
    it, if possible.

    Inputs:
      user_command: a game-playing command from the user
      possible_commands: a list of legal commands at this point in the game.

    Output: If any element of the possible_commands list matches the
      user_command semantically, then return that element of the
      possible_commands list.  Otherwise return the empty string.
      
      This method will never return something not in the list of
    possible commands.


    Some examples:

    >>> normalize_command("east", ("go north", "inv", "look"))
    ""

    >>> normalize_command("n", ("go north", "inv", "look"))
    "go north"

    >>> normalize_command("what am I holding?",  ("go north", "inv", "look"))
    "inv"
    """

@cachier()
@sec.subagent()
def clarify(input_sentence: str) -> str:
    """Given an awkward statement that conveys some important information,
    rewrite the sentence to be clear and coherent.

    Some examples:

    >>> clarify("You have: lamp, umbrella, gold.")
    "You have a lamp, an umbrella, and some gold."
    """

#
# Game play
#

def fpara(paragraph: str, width=60):
    """Nicely format a paragraph-long piece of text."""
    return fill(
        dedent(paragraph).strip(),
        replace_whitespace=True,
        width=width)

class Room(BaseModel):
    name: str
    neighbors: dict[str, str] = Field(default={})
    description: str | None = Field(default=None)
    previously_entered: int = 0
    inv: list[str] = Field(default=[]) # items here
    local_commands: dict[str, Callable] = Field(default={})

    def get_description(self, rooms: list, target_n_examples=2):
        """Return a room description, creating one if needed.
        """
        if self.description is None:
            print(f'LLM: filling in a description of {self.name}')
            # collect descriptions of other rooms as examples
            all_descriptions = [r.description for r in rooms.values() if r.description]
            sample_descriptions = random.sample(all_descriptions, k=target_n_examples)
            # make args cachable
            self.description = fpara(describe_new_room(self.name, tuple(sample_descriptions)))
        return self.description

class Item(BaseModel):
    name: str
    description: str

class Player(BaseModel):
    loc: str  # short name of room you're in
    inv: list[str] = Field(default=[]) # items carried

class Game(BaseModel):
    player: Player
    items: dict[str, Item] = {}
    rooms: dict[str, Room] = {}
    state: dict[str, str] = {}  # for status='won', etc

    def add_room(self, room):
        self.rooms[room.name] = room

    def get_room(self, room_name):
        return self.rooms[room_name]

    def add_item(self, item):
        self.items[item.name] = item

    def get_item(self, item_name):
        return self.items[item_name]

    def _enter_room(self, room_name, direction):
        """Move the player in the given direction into the named room.

        If the room hasn't been created yet, create a simple version
        of it.
        """
        previous_room = self.player.loc
        if not room_name in self.rooms:
            # create a room given its name, assuming you will be able
            # to return to the previous_room by reversing the
            # direction, or going "back".
            opposite_dir = dict(
                north='south', south='north', 
                east='west', west='east')
            dir_dict = {opposite_dir.get(direction, 'back'): previous_room}
            self.rooms[room_name] = Room(
                name=room_name,
                neighbors=dir_dict)
        self.player.loc = self.rooms[room_name].name

    def possible_commands(self):
        """Return a dictionary of possible commands.

        Keys are command names, values are callable functions with no
        parameters.
        """
        commands = {'inv': self.inv, 'look': self.look}
        room = self.rooms[self.player.loc]
        commands.update(
            {f'go {dir}': partial(self.go, direction=dir) for dir in room.neighbors})
        commands.update(
            {f'take {it}': partial(self.take, item_name=it) for it in room.inv})
        commands.update(
            {f'drop {it}': partial(self.drop, item_name=it) for it in self.player.inv})
        commands.update(
            {f'examine {it}': partial(self.examine, item_name=it) for it in self.player.inv})
        commands.update(room.local_commands)
        return commands

    def do_command(self, command):
        """Perform a command.
        """
        possible = self.possible_commands()
        matching_command = normalize_command(command, tuple(possible.keys()))
        print(f'LLM: "{command}" means "{matching_command}"')
        if matching_command:
            possible[matching_command]()
        else:
            player = self.player
            room = self.rooms[player.loc]
            print(fpara(refusal(
                command, 
                room.description,
                list(room.neighbors.keys()),
                player.inv,
                room.inv)))

    #
    # operations invoked by game commands
    #

    def inv(self):
        """List what player is carrying.
        """
        player = self.player
        if not player.inv:
            print('You are not carrying anything.')
        else:
            print(clarify('You have: ' + ', '.join(player.inv)))

    def look(self):
        """Describe the current room and contents.
        """
        room = self.rooms[self.player.loc]
        print(room.get_description(self.rooms))
        if room.inv:
            print('\n' + clarify(
                'You see some items here: '  + ', '.join(room.inv)))
            for item_name in room.inv:
                item = self.items[item_name]
                print('\n' + item.description)

    def take(self, item_name):
        """Take an item from the current room.
        """
        room = self.rooms[self.player.loc]
        room.inv.remove(item_name)
        self.player.inv.append(item_name)
        print(clarify(f'You take: {item_name}'))

    def drop(self, item_name):
        """Drop an item in the current room.
        """
        room = self.rooms[self.player.loc]
        self.player.inv.remove(item_name)
        room.inv.append(item_name)
        print(clarify(f'You drop {item_name}'))

    def examine(self, item_name):
        """Examine an item you have closely.
        """
        print(self.items[item_name].description)

    def go(self, direction):
        """Go to an adjacent room.
        """
        room = self.rooms[self.player.loc]
        next_room_name = room.neighbors.get(direction)
        self._enter_room(next_room_name, direction)
        self.look()

    def save_data(self, filename):
        """Save the core data for the game.
        """
        with open(filename, 'w') as fp:
            fp.write(self.model_dump_json(indent=2))
        print(f'Saved to {filename}.')

    @staticmethod
    def restore_data(filename):
        """Restore the game's data.
        """
        print(f'Loading game data from {filename}.')
        with open(filename) as fp:
            return Game.model_validate_json(fp.read())


    def play(self):
        """Game play loop.
        """
        self.look()
        while 'status' not in self.state:
            try:
                command = input('>> ')
                if command:
                    self.do_command(command)
            except EOFError:
                break
            except Exception as ex:
                # this would be a bug
                print(f"Exception: {ex}")
                print(f"You can't '{command}'")

        if 'status' in self.state:
            print(f'\nYou {self.state["status"]}')
        else:
            print("Bye.")


if __name__ == '__main__':
    game = pyramid_game.make_game()
    play(game)
