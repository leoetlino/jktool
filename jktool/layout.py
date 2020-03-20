import enum
import construct as ct

u8 = ct.Int8ul
u16 = ct.Int16ul
u32 = ct.Int32ul
s8 = ct.Int8sl
s16 = ct.Int16sl
s32 = ct.Int32sl
f32 = ct.Float32l
f64 = ct.Float64l
cstr = ct.CString("utf8")
this = ct.this

Vec2 = f32[2]
Vec3 = f32[3]
Vec4 = f32[4]

CompactVec4 = ct.Struct(
    "_raw" / ct.Rebuild(u8[4], lambda this: [int(x * 255.0) & 0xFF for x in this.v]),
    "v" / ct.Computed(lambda this: [x / 255.0 for x in this._raw]),
)


class PaneType(enum.IntEnum):
    Type0 = 0
    Type1 = 1
    Rect = 2
    Text = 3
    Pane = 4
    PaneEx = 5
    Pane2 = 6
    Pane2Ex = 7


PaneNull = ct.Struct(
    "translate" / Vec3,
)
assert PaneNull.sizeof() == 0xC

Pane1 = ct.Struct(
    "translate" / Vec3,
    "zMultiplier" / f32,
)
assert Pane1.sizeof() == 0x10

PaneRect = ct.Struct(
    "translate" / Vec3,
    "width" / f32,
    "height" / f32,
)
assert PaneRect.sizeof() == 0x14

PaneText = ct.Struct(
    "translate" / Vec3,
    "width" / f32,
    "height" / f32,
    "msgId" / u32,
    "b" / f32,
    "c" / f32,
    "flags" / u16,
    "numEntries" / u16,
    "x" / u8[4],
)
assert PaneText.sizeof() == 0x28

Pane4 = ct.Struct(
    "translate" / Vec3,
    "width" / f32,
    "height" / f32,
    "color" / CompactVec4,
)
assert Pane4.sizeof() == 0x18

Pane5 = ct.Struct(
    "translate" / Vec3,
    "width" / f32,
    "height" / f32,
    "colors" / CompactVec4[4],
)
assert Pane5.sizeof() == 0x24

Pane6 = ct.Struct(
    "translate" / Vec3,
    "width" / f32,
    "height" / f32,
    "rotate" / Vec2,
    "scale" / Vec2,
    "a" / u16,
    "b" / u16,
    "color" / CompactVec4,

)
assert Pane6.sizeof() == 0x2C

Pane7 = ct.Struct(
    "translate" / Vec3,
    "width" / f32,
    "height" / f32,
    "rotate" / Vec2,
    "scale" / Vec2,
    "a" / u16,
    "b" / u16,
    "color" / CompactVec4[4],
)
assert Pane7.sizeof() == 0x38

Pane = ct.Struct(
    "type" / ct.Enum(u16, PaneType),
    "size" / u16,
    "_data_offset" / ct.Tell,
    "data" / ct.Switch(lambda this: int(this.type), {
        0: PaneNull,
        1: Pane1,
        2: PaneRect,
        3: PaneText,
        4: Pane4,
        5: Pane5,
        6: Pane6,
        7: Pane7,
    }),
    ct.Seek(this._data_offset + this.size),
)


class WidgetType(enum.IntEnum):
    Group = 0
    Layout = 1
    MainWidget = 2
    Pane = 3


Widget = ct.Struct(
    "widgetIdx" / ct.Index,
    "flags" / u32,
    "type" / ct.Computed(lambda this: WidgetType(((this.flags << 0x1a) & 0xffffffff) >> 0x1e)),
    "objectIdx" / u16,
    "numChildWidgets" / u16,
    "translate" / Vec3,  # usually (0., 0., 0.)
    "scale" / Vec3,  # usually (1., 1., 1.)
    "rotate" / Vec3,  # usually (0., 0., 0.)
    "x2C" / Vec2,  # usually (0., 0.)
    "x34" / Vec2,  # usually (1., 1.)
    "x3C" / f32,  # usually 0.0
    "color" / CompactVec4,
)
assert Widget.sizeof() == 0x44


class WidgetValueType(enum.IntEnum):
    TranslateX = 0
    TranslateY = 1
    TranslateZ = 2
    ScaleX = 3
    ScaleY = 4
    ScaleZ = 5
    RotateX = 6
    RotateY = 7
    RotateZ = 8
    Visible = 9
    Field24_X = 10
    Field24_Y = 11
    Field2C_X = 12
    Field2C_Y = 13
    Field34 = 14
    ColorR = 15
    ColorG = 16
    ColorB = 17
    ColorA = 18
    Unk = 19


class AnimEntryType(enum.IntEnum):
    Interpolate = 0
    Set = 1
    Add = 2
    AddPositive = 3


AnimKeyframeValueDict = dict()
for i in range(len(WidgetValueType)):
    AnimKeyframeValueDict[i] = f32
AnimKeyframeValueDict[9] = u32
AnimKeyframeValueDict[19] = s32


class AnimKeyframeType(enum.IntEnum):
    Nop = 0
    Lerp = 1
    Type2 = 2
    Type2R = 3
    SetToZero = 4


AnimKeyframe = ct.Struct(
    "frame" / u32,
    "flags" / u16,
    "type" / ct.Computed(lambda this: AnimKeyframeType(this.flags & 0xf)),
    "_x6" / ct.Const(0, ct.Default(u16, 0)),
    "value" / ct.Switch(lambda this: int(this._.valueType), AnimKeyframeValueDict),
)

AnimEntry = ct.Struct(
    "widgetIdx" / u16,
    "valueType" / ct.Enum(u8, WidgetValueType),
    "_x3" / ct.Const(0, ct.Default(u8, 0)),
    "numKeyframes" / ct.Rebuild(u16, lambda this: len(this.data) if int(this.type) == 0 else 0),
    "flags" / u16,
    "type" / ct.Computed(lambda this: AnimEntryType(this.flags & 3)),
    "maxFrameIdx" / u32,

    "data" / ct.Switch(lambda this: int(this.type), {
        0: AnimKeyframe[this.numKeyframes],
        1: f32[this._.startFrame + 1],
        2: f32[this._.startFrame + 1],
        3: f32[this._.startFrame + 1],
    }),
)

Anim = ct.Struct(
    "numEntries" / ct.Rebuild(u16, ct.len_(this.entries)),
    "fps" / u16,
    "startFrame" / u32,
    "entries" / AnimEntry[this.numEntries],
)

Layout = ct.Aligned(0x10, ct.Struct(
    "magic" / ct.Const(b"MFL "),
    "versionMajor" / ct.Const(4, u16),
    "versionMinor" / ct.Const(0, u16),
    "layoutId" / u16,
    "numWidgets" / ct.Rebuild(u16, lambda this: len(this.widgetsNames)),
    "numMainWidgets" / ct.Rebuild(u16, lambda this: len(this.mainWidgetsNames)),
    "numPanes" / ct.Rebuild(u16, lambda this: len(this.panesNames)),
    "numPlayers" / ct.Rebuild(u16, lambda this: len(this.playersNames)),
    "numAnims" / ct.Rebuild(u16, lambda this: len(this.animsNames)),
    "panesOffset" / ct.Default(u32, 0),
    "animsOffset" / ct.Default(u32, 0),
    "namesOffset" / ct.Default(u32, 0),

    "widgets" / Widget[this.numWidgets],

    # ct.Seek(this.panesOffset),
    "_panesOffset" / ct.Tell,
    ct.Pointer(0x14, ct.Rebuild(u32, this._panesOffset)),
    "panes" / Pane[this.numPanes],

    # ct.Seek(this.animsOffset),
    "_animsOffset" / ct.Tell,
    ct.Pointer(0x18, ct.Rebuild(u32, this._animsOffset)),
    "anims" / Anim[this.numAnims],

    # ct.Seek(this.namesOffset),
    "_namesOffset" / ct.Tell,
    ct.Pointer(0x1C, ct.Rebuild(u32, this._namesOffset)),
    "name" / cstr,
    "mainWidgetsNames" / cstr[this.numMainWidgets],
    "panesNames" / cstr[this.numPanes],
    "widgetsNames" / cstr[this.numWidgets],
    "playersNames" / cstr[this.numPlayers],
    "animsNames" / cstr[this.numAnims],
))

PackageFile = ct.Struct(
    "x" / u16,
    "id" / u8,
    "flags" / u8,
    "name" / cstr,
)

Package = ct.Aligned(0x10, ct.Struct(
    "magic" / ct.Const(b"MFPK"),
    "versionMajor" / ct.Const(3, u16),
    "versionMinor" / ct.Const(0, u16),
    "numFiles" / ct.Rebuild(u16, lambda this: len(this.files)),
    ct.Padding(6),
    "files" / ct.Aligned(4, PackageFile)[this.numFiles],
))

Project = ct.Aligned(0x10, ct.Struct(
    "magic" / ct.Const(b"MFPJ"),
    "versionMajor" / ct.Const(3, u16),
    "versionMinor" / ct.Const(0, u16),
    "numPackages" / ct.Rebuild(u16, lambda this: len(this.packages)),
    "numLayouts" / ct.Rebuild(u16, lambda this: len(this.layouts)),
    "numResourceExts" / ct.Rebuild(u16, lambda this: len(this.resourceExts)),
    "_xe" / ct.Const(0, u16),
    "namesOffset" / u32,
    "unk1" / u32[3],
    "numTextures" / u32,
    "unk2" / u32[3],

    ct.Seek(this.namesOffset),
    "packages" / cstr[this.numPackages],
    "layouts" / cstr[this.numLayouts],
    "resourceExts" / cstr[this.numResourceExts],
))
