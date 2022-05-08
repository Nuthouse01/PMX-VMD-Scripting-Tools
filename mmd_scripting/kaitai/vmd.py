# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Vmd(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header = Vmd.THeader(self._io, self, self._root)
        if not (self._io.is_eof()):
            self.num_boneframes = self._io.read_u4le()

        if not (self._io.is_eof()):
            self.boneframes = [None] * (self.num_boneframes)
            for i in range(self.num_boneframes):
                self.boneframes[i] = Vmd.TBoneframe(self._io, self, self._root)


        if not (self._io.is_eof()):
            self.num_morphframes = self._io.read_u4le()

        if not (self._io.is_eof()):
            self.morphframes = [None] * (self.num_morphframes)
            for i in range(self.num_morphframes):
                self.morphframes[i] = Vmd.TMorphframe(self._io, self, self._root)


        if not (self._io.is_eof()):
            self.num_camframes = self._io.read_u4le()

        if not (self._io.is_eof()):
            self.camframes = [None] * (self.num_camframes)
            for i in range(self.num_camframes):
                self.camframes[i] = Vmd.TCamframe(self._io, self, self._root)


        if not (self._io.is_eof()):
            self.num_lightframes = self._io.read_u4le()

        if not (self._io.is_eof()):
            self.lightframes = [None] * (self.num_lightframes)
            for i in range(self.num_lightframes):
                self.lightframes[i] = Vmd.TLightframe(self._io, self, self._root)


        if not (self._io.is_eof()):
            self.num_shadowframes = self._io.read_u4le()

        if not (self._io.is_eof()):
            self.shadowframes = [None] * (self.num_shadowframes)
            for i in range(self.num_shadowframes):
                self.shadowframes[i] = Vmd.TShadowframe(self._io, self, self._root)


        if not (self._io.is_eof()):
            self.num_ikdispframes = self._io.read_u4le()

        if not (self._io.is_eof()):
            self.ikdispframes = [None] * (self.num_ikdispframes)
            for i in range(self.num_ikdispframes):
                self.ikdispframes[i] = Vmd.TIkdispframe(self._io, self, self._root)


        self.dangle = self._io.read_bytes_full()

    class THeader(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.magic = self._io.read_bytes(21)
            if not self.magic == b"\x56\x6F\x63\x61\x6C\x6F\x69\x64\x20\x4D\x6F\x74\x69\x6F\x6E\x20\x44\x61\x74\x61\x20":
                raise kaitaistruct.ValidationNotEqualError(b"\x56\x6F\x63\x61\x6C\x6F\x69\x64\x20\x4D\x6F\x74\x69\x6F\x6E\x20\x44\x61\x74\x61\x20", self.magic, self._io, u"/types/t_header/seq/0")
            self.verstring = (self._io.read_bytes(4)).decode(u"shift-jis")
            self._unnamed2 = self._io.read_bytes(5)
            self.modelname = (self._io.read_bytes((10 if self.verstring == u"file" else 20))).decode(u"shift-jis")


    class TIkdispframe(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.framenum = self._io.read_u4le()
            self.visible = self._io.read_u1()
            self.num_ikbones = self._io.read_u4le()
            self.ikbones = [None] * (self.num_ikbones)
            for i in range(self.num_ikbones):
                self.ikbones[i] = Vmd.TIkbone(self._io, self, self._root)



    class TShadowframe(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.framenum = self._io.read_u4le()
            self.mode = self._io.read_u1()
            self.dist = self._io.read_f4le()


    class TMorphframe(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.name = self._io.read_bytes(15)
            self.framenum = self._io.read_u4le()
            self.value = self._io.read_f4le()


    class TBoneframe(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.name = self._io.read_bytes(15)
            self.framenum = self._io.read_u4le()
            self.pos = Vmd.TVec3(self._io, self, self._root)
            self.rot = Vmd.TVec4(self._io, self, self._root)
            self.interp = self._io.read_bytes(64)


    class TLightframe(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.framenum = self._io.read_u4le()
            self.color = Vmd.TVec3(self._io, self, self._root)
            self.pos = Vmd.TVec3(self._io, self, self._root)


    class TVec3(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.xyz = [None] * (3)
            for i in range(3):
                self.xyz[i] = self._io.read_f4le()



    class TCamframe(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.framenum = self._io.read_u4le()
            self.dist = self._io.read_f4le()
            self.pos = Vmd.TVec3(self._io, self, self._root)
            self.rot = Vmd.TVec3(self._io, self, self._root)
            self.interp = self._io.read_bytes(24)
            self.fov = self._io.read_u4le()
            self.is_perspective = self._io.read_u1()


    class TIkbone(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.bname = self._io.read_bytes(20)
            self.ik_enable = self._io.read_u1()


    class TVec4(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.xyzw = [None] * (4)
            for i in range(4):
                self.xyzw[i] = self._io.read_f4le()




