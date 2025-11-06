"""Todo:

game.examine(item_name)

n_th_review(n, description)

@config examples
"""

from cachier import cachier
from functools import partial
import random

from pydantic import BaseModel, Field
from textwrap import dedent, fill, wrap
from typing import Callable

import secretagent as sec

#
# LLM access
#

def play(game):
    """Game play loop.
    """
    game.look()
    while True:
        try:
            command = input('>> ')
            if not command:
                break
            game.do_command(command)
        except EOFError:
            break
        except Exception as ex:
            print(f"Exception: {ex}")
            print(f"You can't '{command}'")
    print("Bye.")


@cachier()
@sec.subagent()
def refusal(command: str, room_description: str, player_inv: list[str], room_inv: list[str]) -> str:
    """Explain why a command is not applicable here.

    Inputs:
      command: the inapplicable command issued by the player
      room_description: a description of the current room
      player_inv: a list of the items carried by the player.

    Output:
      An explanation as to why the command is invalid.

    Some examples:

    >>> refusal("go south", "You are in a vast desert with an old pyramid just north of you", [], [])
    "The desert is much too hostile to explore without the proper equipment."
    
    >>> refusal("examine whip", "You are in the entrance to a dark tunnel", ["fedora", "gun"], [])
    "You don't see anything like that here."

    >>> refusal("talk to the mummy", "You are in a burial chamber.", [], [])
    "It seems unlikely that the mummy will answer, since it has been dead for a while."
    """

@cachier()
@sec.subagent()
def describe_new_room(room_name: str, nearby_room_descriptions: tuple[str]) -> str:
    """Return a 2-3 sentence description of a room in a text adventure game.

    Inputs:
      room_name: a short name of the room
      nearby_room_descriptions: a tuple of descriptions of nearby rooms.

    Output:
      a description of the room, similar in flavor to the
    nearby rooms.
    """

@cachier()
@sec.subagent()
def normalize_command(user_command: str, possible_commands: list[str]) -> str:
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

    >>> normalize_command("north", ["go north", "inv", "look"])
    "go north"

    >>> normalize_command("east", ["go north", "inv", "look"])
    ""

    >>> normalize_command("what am I holding?",  ["go north", "inv", "look"]
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
    """Format a paragraph-long text description."""
    return fill(
        dedent(paragraph).strip(),
        replace_whitespace=True,
        width=width)

class Room(BaseModel):
    name: str
    neighbors: dict[str, str]
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
            description = describe_new_room(self.name, tuple(sample_descriptions))
        return self.description

class Item(BaseModel):
    name: str
    description: str

class Player(BaseModel):
    loc: str  # short name of room you're in
    inv: list[str] = Field(default=[]) # items carried

class Game(BaseModel):
    player: Player
    items: dict[str, Item] = Field(default={})
    rooms: dict[str, Room] = Field(default={})

    def _enter_room(self, room_name, direction):
        """Move the player intoin the given direction into the named room.

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
        commands.update(room.local_commands)
        return commands

    def do_command(self, command):
        """Perform a command.
        """
        possible = self.possible_commands()
        matching_command = normalize_command(command, list(possible.keys()))
        print(f'LLM: I think "{command}" means "{matching_command}"')
        if matching_command:
            possible[matching_command]()
        else:
            player = self.player
            room = self.rooms[player.loc]
            print(fpara(refusal(command, room.description, player.inv, room.inv)))

    def inv(self):
        """List what player is carrying.
        """
        player = self.player
        if not player.inv:
            print('You are not carrying anything.')
        else:
            print(clarify('You have: ', ', '.join(player.inv)))

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

    def go(self, direction):
        """Go to an adjacent room.
        """
        room = self.rooms[self.player.loc]
        next_room_name = room.neighbors.get(direction)
        if next_room_name is None:
            print(f"You can't go {direction}.")
        else:
            self._enter_room(next_room_name, direction)
            self.look()

    def save(self, filename):
        """Save the gane.
        """
        with open(filename, 'w') as fp:
            fp.write(self.model_dump_json(indent=2))
        print(f'Saved to {filename}.')

    @staticmethod
    def restore(filename):
        """Restore the game.
        """
        with open(filename) as fp:
            return Game.model_validate_json(fp.read())
        

def make_game():
    game = Game(
        player=Player(
            loc='in front',
            inv = ['bullwhip', 'fedora']),
        items={
            'bullwhip': Item(
                name='bullwhip',
                description='The bullwhip is old and worn, made of black leather.'),
            'fedora': Item(
                name='fedora',
                description='The fedora is gray and stained but comfortable-looking.'),
            'crowbar': Item(
                name='crowbar',
                description=fpara("""
                The crowbar is about 4 feet long, and made of sturdy iron.
                You guess that it was abandoned by some previous grave
                robbers. There are no markings on it, and it could have
                been made ten years ago or two hundred.
                """),
            ),
        },
        rooms = {
            'in front': Room(
                name='in front',
                description=fpara("""
                You're in in front to an ancient pyramid.  The structure is
                old and crumbling, and looks to be thousands of years old.
                All around you is a wind-swept desert, dry and completely empty.
                To the north of you is a tunnel into the side of the pyramid,
                probably made by grave robbers long ago.
                """),
                neighbors=dict(north='tunnel entrance'),
            ),
            'tunnel entrance': Room(
                name='tunnel entrance',
                description=fpara("""
                The tunnel leads up into the ancient pyramid at a steep angle.
                Faded hieroglyphics are painted on the huge stones that
                line the tunnel walls, along with dim images of animal-headed
                figures.  Partway up, a cedar door with a broken seal is
                hanging open.
                """),
                neighbors=dict(
                    south='in front', north='tunnel end', east='empty room'),
            inv=['crowbar'],
            ),
            'tunnel end': Room(
                name='tunnel end',
                description=fpara("""
                The tunnel ends at heavy stone door.
                """),
                neighbors=dict(south='tunnel entrance'),
            ),
            'thrown room': Room(
                name='thrown room',
                neighbors=dict(south='tunnel end'),
                description=fpara("""
                You are surrounded by the treasures of a long-dead pharoah.
                """),
            ),
        }
    )
    # attach special actions to locations
    def open_stone_door():
        # local for 'tunnel end'
        if 'crowbar' in game.player.inv:
            print('Using the crowbar, you are able to force the stone door open!')
            game.rooms['tunnel end'].neighbors['north'] = 'thrown room'
        else:
            print('The stone door seems to be immovable.')

    game.rooms['tunnel end'].local_commands['open door'] = open_stone_door

    return game

if __name__ == '__main__':
    sec.configure(service="anthropic", model="claude-haiku-4-5-20251001")
    #sec.configure(service="anthropic", model="claude-sonnet-4-5-20250929")
    game = make_game()
    play(game)

    
