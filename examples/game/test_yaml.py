from cachier import cachier
import json
from pprint import pprint
import yaml

import secretagent as sec

from game import Game, Player, Room, Item, fpara

@cachier()
@sec.subagent(echo_call=True)
def opposite_direction(direction: str) -> str:
    """Given a direction, return the opposite. 

    Examples:
    >>> opposite_direction('north')
    'south'
    """

@cachier()
@sec.subagent(echo_call=True)
def describe_new_room(room_name: str, hint: str, nearby_room_description: str) -> str:
    """Return a 2-3 sentence description of a room in a text adventure game.

    The game is played in a dry pyramid in a desert, so descriptions
    should not mention dripping water or dampness.  The player does
    not carry a torch, and the source of light is never mentioned.
    The rooms are all looted by grave robbers long ago, and contain no
    obvious valuables.

    Inputs:
      room_name: a short name of the room
      hint: a short version of the description being generated
      nearby_room_description: a description of a nearby room.

    Output:

      a description of a room connected to the nearby room.  The
    description should be consistent with the hint, and contain some
    details different from the nearby room.
    """

def make_path(game: Game, start:str, end:str, dirs:str, name:str, hint:str):
    """Create a path from start_room to end_room following directions
    """
    directions = dirs.split(' ')
    room = game.get_room(start)
    for i, d in enumerate(directions):
        if i == len(directions) - 1:
            next_room = game.get_room(end)
        else:
            next_name = f'{name} {i}'
            next_descr = fpara(describe_new_room(next_name, hint, room.description))
            next_room = Room(
                name=next_name,
                description=next_descr)
            game.add_room(next_room)
        room.neighbors[d] = next_room.name
        next_room.neighbors[opposite_direction(d)] = room.name
        room = next_room

if __name__ == '__main__':

    sec.configure(service="anthropic", model="claude-haiku-4-5-20251001")

    with open('pyramid.yaml') as fp:
        data = yaml.load(fp, Loader=yaml.FullLoader)
        
        # collect the paths to create
        # re-format all the descriptions with fpara

        paths_to_make = []
        for room_name in data['rooms']:
            room = data['rooms'][room_name]
            if 'PATH' in room['neighbors']:
                path_kw = room['neighbors']['PATH']
                paths_to_make.append(path_kw)
                del room['neighbors']['PATH']
            if 'description' in room:
                room['description'] = fpara(room['description'])

        # create the game
        game = Game.model_validate(data)
        for path_kw in paths_to_make:
            print('making path', path_kw)
            make_path(game, **path_kw)
            
