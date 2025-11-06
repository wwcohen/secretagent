import re

text = """
<thought>
The function should produce a paragraph-length description of a room called "tunnel end" that is consistent with the flavor of the nearby rooms provided.

Looking at the nearby room descriptions:
1. The first describes a tunnel leading up into a pyramid with hieroglyphics, animal-headed figures, and a cedar door with a broken seal
2. The second describes the front of an ancient pyramid in a desert with a tunnel entrance

The "tunnel end" should be at the end of the tunnel, so it should:
- Continue the Egyptian/pyramid theme
- Be consistent with the ancient, mysterious atmosphere
- Possibly describe what's at the end of the tunnel (perhaps a chamber, burial site, or treasure room)
- Use similar descriptive language and tone
- Be paragraph-length

I should create a description that feels like a natural continuation of the tunnel journey, maintaining the archaeological/ancient Egyptian aesthetic.
</thought>


<answer>

The tunnel opens into a vast chamber, its ceiling lost in shadow high above.
The walls are covered in more hieroglyphics and faded murals depicting
scenes of the afterlife and divine judgment. Massive stone pillars support
the chamber, their surfaces carved with the likenesses of long-dead pharaohs.
In the center of the room stands a stone sarcophagus, its lid partially
shifted aside, revealing only darkness within. The air is thick with dust
and the smell of ages past, and your footsteps echo eerily off the ancient
stone.

</answer>
"""

m = re.search(r'<answer>(.*)</answer>', text, re.DOTALL|re.MULTILINE)
print(m)
print('----')
print(m.group(1).strip())
print('----')


