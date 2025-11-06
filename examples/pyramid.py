import json

from game import Game, Player, Room, Item, fpara

def make_game_data():
    """Generate the core data structures of a game.
    """
    game_data = Game(
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
                """)),
            'knife': Item(
                name='knife',
                description=fpara("""
                The knife is dusty and so dark it is hard to focus on,
                but knife blade is about 10 inches long, made of
                obsidian, with razor-sharp edges. The handle is
                embossed and uncomfortable to hold, and studded with 
                jet-black pearls.
                """)),
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

            # main tunnel
            'tunnel entrance': Room(
                name='tunnel entrance',
                description=fpara("""
                You're at the entrance to a wide tunnel, which leads up
                into the ancient pyramid at a steep angle.  Faded
                hieroglyphics are painted on the huge stones that line
                the tunnel walls, along with dim images of
                animal-headed figures.  In the east, a cedar door with
                a broken seal is hanging partly open.
                """),
                neighbors=dict(
                    south='in front', north='tunnel midpoint', east='east passage 1'),
            ),
            'tunnel midpoint': Room(
                name='tunnel midpoint',
                neighbors=dict(south='tunnel entrance', north='tunnel end'),
            ),
            'tunnel end': Room(
                name='tunnel end',
                description=fpara("""
                The tunnel ends at huge sarcophagus, with a heavy stone lid.
                The lid is ornately carved but much to heavy to remove.
                """),
                neighbors=dict(south='tunnel midpoint'),
            ),
            # deadend until you open the sarcophagus with the crowbar
            'sarcophagus': Room(
                name='sarcophagus',
                description=fpara(
                    """ Aside from you, the sarcophagus
                    is empty...in fact it contains less than nothing.
                    The only thing inside is a dim passage that slants down.
                    """),
                neighbors=dict(down='passage down', south='tunnel end')
            ),
            'passage down': Room(
                name='passage down',
                description=fpara(
                    """The passage twists steeply downward and to the west.
                    Massive stone blocks line the sides, and they are roughly
                    cut, without ornamentation."""),
                neighbors=dict(up='sarcophagus', west='west passage'),
            ),
            'west passage': Room(
                name='west passage',
                neighbors=dict(east='passage down', down='steep stairs')
            ),
            'steep stairs': Room(
                name='steep stairs',
                neighbors=dict(up='west passage', down='treasure room doorway')
            ),
            'treasure room doorway': Room(
                name='treasure room doorway',
                # deadend till you cut the chains
                neighbors=dict(up='steep stairs'),
                description=fpara(
                    """As the stairs descend they seem to be no longer
                    in the pyramid but cut into the living rock.  The
                    walls are cool and damp.  At the bottom of the stairs
                    is a double doorway, with huge rings on either side.
                    The rings are linked by black chains wrought of meteoric
                    steel, intertwined with silver wires bent into
                    strange symbols that seem to writhe and twist when you
                    look at them.
                    """),
            ),

            # spur off to the east from entrance leading to knife
            'east passage 1': Room(
                name='east passage 1',
                neighbors=dict(west='tunnel entrance', east='east passage 2'),
                inv=['crowbar']
            ),
            'east passage 2': Room(
                name='east passage 2',
                neighbors=dict(west='east passage 1', east='raven room'),
            ),
            'raven room': Room(
                name='raven room',
                description=fpara("""
                The passage widens out to a large room.  Midway
                through the room, in a niche on the south wall, is a
                life-sized stone statue of man with the head of a raven.
                """),
                neighbors=dict(west='east passage 2', east='raven statue')
            ),
            'raven statue': Room(
                name='raven statue',
                description=fpara("""
                The paint on the statue is faded, but visible, and
                when it was new it must have been magnificent.  The
                eyes have been torn out: perhaps they were jewels and
                were stolen by robbers.  

                In spite of this it somehow seems that the statue
                follows you with its eyes as you cross the room,
                especially when you try and move past it, to the east.
                """),
                neighbors=dict(west='raven room'),
            ),
            # blocked till you solve the puzzle...
            'raven room east': Room(
                name='raven room east',
                description=fpara("""
                There's nothing much in the east side of the room: no
                exits, no more statues.
                """),
                inv=['knife'],
                neighbors=dict(west='raven statue')
            ),
        }
    )
    return game_data

if __name__ == "__main__":
    game = make_game_data()
    game.save_data('pyramid.json')
