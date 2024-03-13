from enum import IntEnum, auto

class FoveaShape(IntEnum):
    UNIFORM = 0
    CIRCLE = auto()
    SPLIT_HORIZONTALLY = auto()
    SPLIT_VERTICALLY = auto()

class FoveaInputType(IntEnum):
    NONE = 0
    PROCEDURAL = auto()
    MOUSE = auto()

class FoveaMovePattern(IntEnum):
    LISSAJOUS = 0
    MOVE_AND_STAY = auto()

class SelectionMode(IntEnum):
    UNWEIGHTED = 0
    WEIGHTED = auto()
    LINEAR = auto()
    STEP = auto()
    LOGISTIC = auto()

class NormalizationMode(IntEnum):
    NONE = 0
    LUMINANCE = auto()
    VARIANCE = auto()
    STANDARD_DEVIATION = auto()

    LUM = LUMINANCE
    VAR = VARIANCE
    STD = STANDARD_DEVIATION
