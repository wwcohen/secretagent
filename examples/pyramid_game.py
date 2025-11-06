"""Todo:

game.examine(item_name)

n_th_review(n, description)

@config with examples?
"""

from game import Game, fpara

def make_game():
    game = Game.restore_data('pyramid.json')

    def open_sarcophagus():
        # only can do this with the crowbar
        if 'crowbar' in game.player.inv:
            print('Using the crowbar, you are able to force the lid of the sarcophagus aside.')
            room = game.rooms['tunnel end']
            room.description = fpara(
                """There's a stone sarcophagus at the end of the
                tunnel, with the lid pushed aside. You can't see into
                the sarcophagus without getting practically inside
                it.""")
            room.neighbors['inside'] = 'sarcophagus'
            room.neighbors['inside the sarcophagus'] = 'sarcophagus'
        else:
            print('The lid is much too heavy to move.')
    game.rooms['tunnel end'].local_commands['open sarcophagus with crowbar'] = open_sarcophagus

    def neutralize_raven():
        #how to get past the raven statue
        if 'fedora' in game.player.inv:
            print('The hat slips down and covers the eyes of the statue.  Much better!')
            room = game.rooms['raven statue']
            # the room changes and you can't get the hat back
            game.player.inv.remove('fedora')
            room.description = fpara(
                """There is statue here of a man with a raven's head
                wearing a hat.  Somehow it seems to resent the
                hat...and you don't feel inclined to get close to it.
                """)
            room.neighbors['east'] = 'raven room east'
    game.rooms['raven statue'].local_commands['put fedora on raven statue'] = neutralize_raven

    def open_treasure_room():
        if 'knife' in game.player.inv:
            print(fpara(
                """The chains seem to melt away under the sharp edge
                of the sacred knife, and the doors ponderously swing
                open.  Inside is an untouched royal tomb, where
                countless treasures are laid out around a golden
                sarcophagus.
                """))
            game.status = 'won'
    game.rooms['treasure room doorway'].local_commands['cut chains with knife'] = open_treasure_room

    return game
