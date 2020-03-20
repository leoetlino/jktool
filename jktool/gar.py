# Copyright 2018 leoetlino <leo@leolam.fr>
# Licensed under GPLv2+
import io
import math
from operator import itemgetter
from pathlib import Path
import struct
import typing
from dataclasses import dataclass
from collections import defaultdict

_NUL_CHAR = b'\x00'
_Header = struct.Struct("<4sIHHIII8s")
_FileEntry = struct.Struct('<III')

class Gar:
    class File(typing.NamedTuple):
        offset: int
        data: memoryview

    def __init__(self, data: typing.Union[bytes, memoryview]) -> None:
        self._data = memoryview(data)
        self._files: typing.Dict[str, Gar.File] = dict()

        magic, size, num_types, num_files, types_offset, info_offset, data_offsets_offset, creator = _Header.unpack_from(self._data, 0)
        if magic != b'GAR\x02':
            raise ValueError("Invalid magic: %s (expected 'GAR\\x02')" % magic)

        offset = info_offset
        for i in range(num_files):
            file_size, file_stem_offset, file_name_offset = _FileEntry.unpack_from(self._data, offset)
            name = self._read_string(file_name_offset)
            file_offset: int = struct.unpack_from('<I', self._data, data_offsets_offset + 4 * i)[0]
            self._files[name] = self.File(offset=file_offset,
                                          data=self._data[file_offset:file_offset+file_size])
            offset += _FileEntry.size

    def get_files(self) -> dict:
        return self._files

    def get_file_offsets(self) -> typing.List[typing.Tuple[str, int]]:
        offsets: list = []
        for name, file in self._files.items():
            offsets.append((name, file.offset))
        return sorted(offsets)

    def guess_default_alignment(self) -> int:
        if len(self._files) <= 2:
            return 4
        gcd = next(iter(self._files.values())).offset
        for node in self._files.values():
            gcd = math.gcd(gcd, node.offset)
        return gcd

    def _read_u32(self, offset: int) -> int:
        return struct.unpack_from('>I', self._data, offset)[0]
    def _read_string(self, offset: int) -> str:
        end = self._data.obj.find(_NUL_CHAR, offset) # type: ignore
        return bytes(self._data[offset:end]).decode('utf-8')

def _align_up(n: int, alignment: int) -> int:
    return (n + alignment - 1) & -alignment

def _write(stream: typing.BinaryIO, data: bytes, offset: int) -> int:
    current_pos = stream.tell()
    stream.seek(offset)
    stream.write(data)
    stream.seek(current_pos)
    return len(data)

class GarWriter:
    @dataclass
    class File:
        def __init__(self, name: str, data: bytes, type: str = "") -> None:
            self.name = name
            self.data = data
            if type:
                self.type = type
            else:
                self.type = name.split(".")[1]

        name: str
        data: typing.Union[memoryview, bytes]
        type: str
        _idx: int = -1

    def __init__(self) -> None:
        self.files: typing.Dict[str, GarWriter.File] = dict()
        self._default_alignment = 4

    def set_default_alignment(self, alignment: int) -> None:
        self._default_alignment = alignment

    def _get_alignment_for_file(self, file: File) -> int:
        return self._default_alignment

    def get_file_offsets(self) -> typing.List[typing.Tuple[str, int]]:
        offsets: list = []
        data_offset = 0x10 + _FileEntry.size * len(self.files)
        sorted_names = sorted(self.files.keys())
        for name in sorted_names:
            data_offset += len(name) + 1
        for name in sorted_names:
            alignment = self._get_alignment_for_file(self.files[name])
            data_offset = _align_up(data_offset, alignment)
            offsets.append((name, data_offset))
            data_offset += len(self.files[name].data)
        return offsets

    def write(self, stream: typing.BinaryIO) -> int:
        file_types: typing.DefaultDict[str, typing.List[GarWriter.File]] = defaultdict(list)
        file_types["unknown"] = []
        for i, file in enumerate(self.files.values()):
            file_types[file.type].append(file)
            file._idx = i

        # GAR header
        stream.seek(_Header.size)

        # Types
        types_offset = stream.tell()
        for type_name, files in file_types.items():
            stream.write(self._u32(len(files)))
            # File indices offset
            stream.write(self._u32(0xffffffff))
            # Name offset
            stream.write(self._u32(0xffffffff))
            # ???
            stream.write(self._u32(0xffffffff))

        for i, (type_name, files) in enumerate(file_types.items()):
            entry_offset = types_offset + i * 0x10

            # File indices
            if files:
                _write(stream, self._u32(stream.tell()), entry_offset + 4)
                for file in files:
                    stream.write(self._u32(file._idx))

            # Type name
            _write(stream, self._u32(stream.tell()), entry_offset + 8)
            stream.write(type_name.encode())
            stream.write(_NUL_CHAR)
            stream.seek(_align_up(stream.tell(), 4))

        # File info
        file_info_offset = stream.tell()
        for file in self.files.values():
            stream.write(self._u32(len(file.data)))
            # File stem offset
            stream.write(self._u32(0xffffffff))
            # File name offset
            stream.write(self._u32(0xffffffff))

        for i, file in enumerate(self.files.values()):
            entry_offset = file_info_offset + i * 0xC
            _write(stream, self._u32(stream.tell()), entry_offset + 8)
            stream.write(file.name.encode())
            stream.write(_NUL_CHAR)
            _write(stream, self._u32(stream.tell()), entry_offset + 4)
            stream.write(file.name.split(".")[0].encode())
            stream.write(_NUL_CHAR)
            stream.seek(_align_up(stream.tell(), 4))

        # Data offsets
        data_offsets_offset = stream.tell()
        stream.seek(stream.tell() + 4 * len(self.files))

        # File data
        max_alignment = 1
        for i, file in enumerate(self.files.values()):
            alignment = self._get_alignment_for_file(file)
            max_alignment = (max_alignment * alignment) // math.gcd(max_alignment, alignment)
            stream.seek(_align_up(stream.tell(), alignment))
            _write(stream, self._u32(stream.tell()), data_offsets_offset + 4 * i)
            stream.write(file.data) # type: ignore

        size = stream.tell()
        stream.seek(0)
        stream.write(_Header.pack(b"GAR\x02", size, len(file_types), len(self.files), types_offset, file_info_offset, data_offsets_offset, b"jenkins"))

        return max_alignment

    def _u32(self, value: int) -> bytes:
        return struct.pack('<I', value)

