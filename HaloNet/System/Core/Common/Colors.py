class Color:
    Black = 0
    Blue = 1
    Green = 2
    Cyan = 3
    Red = 4
    Purple = 5
    Brown = 6
    LightGray = 7
    DarkGray = 8
    LightBlue = 9
    LightGreen = 10
    LightCyan = 11
    LightRed = 12
    LightPurple = 13
    Yellow = 14
    White = 15
    Standard = White

ColorPatternMappingInfo = {

    Color.Black:        (0, 30),
    Color.Blue:         (0, 34),
    Color.Green:        (0, 32),
    Color.Cyan:         (0, 36),
    Color.Red:          (0, 31),
    Color.Purple:       (0, 35),
    Color.Brown:        (0, 33),
    Color.DarkGray:     (0, 38),

    Color.LightGray:    (1, 37),
    Color.LightBlue:    (1, 34),
    Color.LightGreen:   (1, 32),
    Color.LightCyan:    (1, 36),
    Color.LightRed:     (1, 31),
    Color.LightPurple:  (1, 35),
    Color.Yellow:       (1, 33),
    Color.White:        (1, 30),

}

ColorPatternMapping = dict()

for color, (pattern_style, pattern_color) in ColorPatternMappingInfo.items():
    ColorPatternMapping[color] = f"\033[{pattern_style};{pattern_color}m"
