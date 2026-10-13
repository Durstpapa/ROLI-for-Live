"""Map Live scales to the keyboard's 19 built-in scales by interval set (exact matches only).

Bitmasks from roli_blocks_basics littlefoot/scripts/LittleFootLibrary/Scale.littlefoot;
bit n = semitone n above the root.
"""

CHROMATIC = 18

BUILTIN_SCALES = [
    (0xAB5, 'Major'),
    (0x5AD, 'Minor'),
    (0x9AD, 'Harmonic Minor'),
    (0x4A5, 'Pentatonic Neutral'),
    (0x295, 'Pentatonic Major'),
    (0x4A9, 'Pentatonic Minor'),
    (0x4E9, 'Blues'),
    (0x6AD, 'Dorian'),
    (0x5AB, 'Phrygian'),
    (0xAD5, 'Lydian'),
    (0x6B5, 'Mixolydian'),
    (0x56B, 'Locrian'),
    (0x555, 'Whole Tone'),
    (0xB6D, 'Arabic (A)'),
    (0x575, 'Arabic (B)'),
    (0x8D1, 'Japanese'),
    (0x8B1, 'Ryukyu'),
    (0x57B, '8-Tone Spanish'),
    (0xFFF, 'Chromatic'),
]

_BY_MASK = dict((mask, index) for index, (mask, _) in enumerate(BUILTIN_SCALES))


def intervals_to_mask(intervals):
    mask = 0
    for i in intervals:
        mask |= 1 << (int(i) % 12)
    return mask


def builtin_index(intervals):
    """Return the built-in scale index with exactly these intervals, or None."""
    return _BY_MASK.get(intervals_to_mask(intervals))
