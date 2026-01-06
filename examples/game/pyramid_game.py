"""
status:
  - test_yaml.py is mostly working
  - pyramid.yaml is the current layout (up to raven status)
  - save/restore in json still works

  - maybe add puzzle links (as strings) to the yaml?
     - as local_commands[special action] = None ?

 - bullwhip puzzle
 - feather-guided maze in a cavern?
   (4x4 grid, add random edges until corners connect)

https://www.bbc.com/news/science-environment-41845445
- from entrance 
  - down to junction 1
    - from junction 1 up toward junction 2 (blocked) 
      - from junction 2 across to queens chamber
        - puzzle: raven statue, pass to get eyes, crowbar
        - puzzle: use eyes to get feather
    - from junction 1 down to cavern (with crowbar)
      - from cavern: puzzle: maze, use feather to find knife 
        - up escape shaft to junction 2
          - from junction 2 up to grand gallery
            - from grand gallery up to wizards chamber (with knife, puzzle: eyes)
            - from wizards chamber up to exit (puzzle: with rope)

"""

from cachier import cachier
import json

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



def save_data(filename):
    """Generate the core data structures and serialize it.
    """
    data = make_data()
    data.save_data(filename)

def make_path(game: Game, start_room:str, end_room:str, direction_str:str, name_prefix:str, hint:str):
    """Create a path from start_room to end_room following directions
    """
    directions = direction_str.split(' ')
    room = game.get_room(start_room)
    for i, d in enumerate(directions):
        if i == len(directions) - 1:
            next_room = game.get_room(end_room)
        else:
            next_name = f'{name_prefix} {i}'
            next_descr = fpara(describe_new_room(next_name, hint, room.description))
            next_room = Room(
                name=next_name,
                description=next_descr)
            game.add_room(next_room)
        room.neighbors[d] = next_room.name
        next_room.neighbors[opposite_direction(d)] = room.name
        room = next_room


def make_data():
    """Generate the core data structures for the game
    """
    game = Game(
        player=Player(
            loc='start',
            inv = ['bullwhip', 'fedora', 'phone']),
    )


    # items
    game.add_item(
        Item(
            name='bullwhip',
            description='The bullwhip is old and worn, made of black leather.'))
    game.add_item(
        Item(
            name='fedora',
            description='The fedora is gray and stained but comfortable-looking.'))
    game.add_item(
        Item(
            name='phone',
            description=fpara(
                """The phone is brand-new, state-of-the-art, and carefully engineered
                to be completely useless without an internet connection.
                """)
        ))
    game.add_item(
        Item(
            name='crowbar',
            description=fpara("""
            The crowbar is about 4 feet long, and made of sturdy iron.
            You guess that it was abandoned by some previous grave
            robbers. There are no markings on it, and it could have
            been made ten years ago or two hundred.
            """)))
    game.add_item(
        Item(
            name='knife',
            description=fpara("""
            The knife is dusty and so dark it is hard to focus on,
            but knife blade is about 10 inches long, made of
            obsidian, with razor-sharp edges. The handle is
            embossed and uncomfortable to hold, and studded with 
            jet-black pearls.
            """)))

    # important rooms

    game.add_room(
        Room(
            name='start',
            description=fpara("""
            You're in in front to an ancient pyramid.  The structure is
            old and crumbling, and looks to be thousands of years old.
            All around you is a wind-swept desert, dry and completely empty.
            To the north of you is a tunnel into the side of the pyramid,
            probably made by grave robbers long ago.
            """),
            neighbors=dict(north='entrance'),
        ))
    game.add_room(
        Room(
            name='entrance',
            description=fpara("""
            You're at the entrance to crudely-made narrow tunnel,
            which leads up into the ancient pyramid at a steep angle.
            """),
            neighbors=dict(south='start')
        )) 
    game.add_room(
        Room(
            name='junction 1',
            description=fpara("""
            The narrow tunnel leads into a larger interior room.
            Faded hieroglyphics are painted on the huge stones that
            line the walls, along with dim images of animal-headed
            figures.  In the east, a broken cedar door with a broken
            seal is hanging, partly open.  In the west, there is a
            doorway with only a few remnants of the door that used to
            close it.
            """),
            neighbors=dict(east='east passage', west='west passage'),
        )) 
    make_path(game, 'entrance', 'junction 1', 'north north north', 
              'robbers tunnel', 'a crude narrow tunnel')
    game.add_room(
        Room(
            name='east passage',
            description=fpara("""
            The passage ends at a small room with a huge sarcophagus,
            with a heavy stone lid.  The lid is ornately carved but
            much too heavy to remove.
            """),
            neighbors=dict(west='junction 1'),
        ))
    game.add_room(
        Room(
            name='west passage',
            description=fpara("""
            The passage ends at small room with a huge sarcophagus. A
            broken stone lid lies on the ground next to it, ornately
            carved but severely damaged.
            """),
            # raven room passage blocked till you solve puzzle
            neighbors=dict(east='junction 1'),
        ))
    game.add_room(
        Room(
            name='in west sarcophagus',
            description=fpara(
                """
                You are inside a sarcophagus at the start
                of a dim passage leading north.
                """),
            neighbors=dict(south='west passage'),
        ))
    game.add_room(
        Room(
            name='raven room',
            description=fpara("""
            You are in a large empty room, with empty niches on the
            east and west walls.  Most are empty, but midway through
            the room, in a niche on the east wall, is a life-sized
            stone statue of man with the head of a raven.
            """),
            neighbors=dict(north='raven statue')
        ))
    make_path(game, 'in west sarcophagus', 'raven room', 'north north north', 
              'west passage', 
              'dim passage with pieces of broken statues on the floor')
    game.add_room(
        Room(
            name='raven statue',
            description=fpara("""
            The paint on the statue is faded, but visible, and when it
            was new it must have been magnificent.  The eyes have been
            gouged out: perhaps they were jewels and were stolen by
            robbers.  In spite of this it somehow seems that the
            statue follows you with its eyes as you cross the room,
            especially when you try and move past it, to the north.
            """),
            # north blocked till you solve the puzzle...
            neighbors=dict(south='raven room'),
        ))
    game.add_room(
        Room(
            name='raven room north',
            description=fpara("""
            In the north side of the room, some torn curtains hang
            in a makeshift frame.  There is a bundle of rags on the
            ground about halfway between the statue and the curtains.
            """),
            neighbors=dict(south='raven statue')
        ))



    # blocked until you get crowbar
#    game.add_room(
#        Room(
#            name='sarcophagus',
#            description=fpara(
#                """ Aside from you, the sarcophagus is dry and empty...
#                except for a few scraps of wood and old fragments of linen.
#                The only thing inside is a dim passage that slants down.
#                """),
#            neighbors=dict(south='tunnel end')
#        ))
#    game.add_room(
#        Room(
#            name='treasure room doorway',
#            # deadend till you cut the chains
#            neighbors=dict(up='steep stairs'),
#            description=fpara(
#                """As the stairs descend they seem to be no longer
#                in the pyramid but cut into the living rock.  The
#                walls are cool and damp.  At the bottom of the stairs
#                is a double doorway, with huge rings on either side.
#                The rings are linked by black chains wrought of meteoric
#                steel, intertwined with silver wires bent into
#                strange symbols that seem to writhe and twist when you
#                look at them.
#            """)))
#
    return game

def add_puzzles(game):

    def notice_sarcophagus_passage():
        # should this only happen once???
        print(fpara(
            """
            The sarcophagus conceals a dim passage that slants down and to the north.
            You need to climb inside to follow the passage.
            """))
        game.rooms['west passage'].neighbors['inside'] = 'in west sarcophagus'
    game.rooms['west passage'].local_commands['look in sarcophagus'] = notice_sarcophagus_passage

    def neutralize_raven():
        #how to get past the raven statue
        if 'fedora' in game.player.inv:
            print('The hat slips down and covers the eyes of the statue.  Much better!')
            # the raven statue room changes and you can't get the hat back
            room = game.rooms['raven statue']
            game.player.inv.remove('fedora')
            room.description = fpara(
                """There is statue here of a man with a raven's head
                wearing a comfortable old fedora hat. 
                """)
            room.neighbors['east'] = 'raven room east'
    game.rooms['raven statue'].local_commands['put fedora on raven statue'] = neutralize_raven

#    def open_sarcophagus():
#        # only can do this with the crowbar
#        if 'crowbar' in game.player.inv:
#            print('Using the crowbar, you are able to force the lid of the sarcophagus aside.')
#            room = game.rooms['tunnel end']
#            room.description = fpara(
#                """There's a stone sarcophagus at the end of the
#                tunnel, with the lid pushed aside. You can't see into
#                the sarcophagus without getting practically inside
#                it.""")
#            room.neighbors['inside'] = 'sarcophagus'
#            room.neighbors['inside the sarcophagus'] = 'sarcophagus'
#        else:
#            print('The lid is much too heavy to move.')
#    game.rooms['tunnel end'].local_commands['open sarcophagus with crowbar'] = open_sarcophagus

#
#    def open_treasure_room():
#        if 'knife' in game.player.inv:
#            print(fpara(
#                """The chains seem to melt away under the sharp edge
#                of the sacred knife, and the doors ponderously swing
#                open.  Inside is an untouched royal tomb, where
#                countless treasures are laid out around a golden
#                sarcophagus.
#                """))
#            game.status = 'won'
#    game.rooms['treasure room doorway'].local_commands['cut chains with knife'] = open_treasure_room

    return game

def walk_rooms(game, loc, prev_loc='none', prev_dir='start', depth=0, visited=None):
    if visited is None:
        visited = set()
    if loc in visited:
        print(f'{"|  "*depth}{prev_loc}:{prev_dir} => {loc} [again]')
    else:
        visited.add(loc)
        print(f'{"|  "*depth}{prev_loc}:{prev_dir} => {loc}')
        for dir, nextloc in game.get_room(loc).neighbors.items():
            walk_rooms(game, nextloc, loc, dir, depth+1, visited)
            

def walk():
    sec.configure(service="anthropic", model="claude-haiku-4-5-20251001")
    game = make_data()
    walk_rooms(game, game.player.loc)

def play(start=None):
    sec.configure(service="anthropic", model="claude-haiku-4-5-20251001")
    data = make_data()
    game = add_puzzles(data)
    if start is not None:
        game.player.loc = start
    game.play()
