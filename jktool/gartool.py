# Copyright 2018 leoetlino <leo@leolam.fr>
# Licensed under GPLv2+
import argparse
import io
import os
from pathlib import Path
import shutil
import struct
import sys
import typing

from . import gar

def gar_extract(args) -> None:
    archive_path = Path(args.gar)
    with archive_path.open('rb') as f:
        archive = gar.Gar(f.read())
        result_dir = Path(archive_path.parent / archive_path.stem)
        result_dir.mkdir(exist_ok=True)
        for name, file in archive.get_files().items():
            target_path = result_dir / Path(name)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with target_path.open('wb') as target_file:
                target_file.write(file.data)
            print(target_path)
        file_list = "\n".join(archive.get_files().keys())
        (result_dir / "__list__.txt").write_text(file_list)

def gar_list(args) -> None:
    with open(args.gar, 'rb') as f:
        archive = gar.Gar(f.read())
        for name, file in archive.get_files().items():
            extra_info = "[0x%x bytes]" % len(file.data)
            extra_info += " @ 0x%x" % file.offset
            print("%s%s" % (name, ' ' + extra_info if not args.name_only else ''))

def _write_gar(writer: gar.GarWriter, dest_stream: typing.BinaryIO) -> None:
    buf = io.BytesIO()
    buf.seek(0)
    shutil.copyfileobj(buf, dest_stream)

def gar_create(args) -> None:
    directory: Path = Path(args.dir)
    dest_file: str = args.dest

    if not directory.is_dir():
        sys.stderr.write(f'error: {directory} is not a directory. Did you mix up the argument order? (directory that should be archived first, then the target archive)\n')
        sys.exit(1)

    writer = gar.GarWriter()

    if args.default_alignment:
        writer.set_default_alignment(args.default_alignment)

    dest_stream: typing.BinaryIO = open(dest_file, 'wb') if dest_file != '-' else sys.stdout.buffer

    files = (Path(directory) / "__list__.txt").read_text().splitlines()
    for file in files:
        writer.files[file] = gar.GarWriter.File(file, (directory / file).read_bytes())

    _write_gar(writer, dest_stream)

def main() -> None:
    parser = argparse.ArgumentParser(description='Tool to manipulate GAR archives.')

    subparsers = parser.add_subparsers(dest='command', help='Command')
    subparsers.required = True

    x_parser = subparsers.add_parser('extract', description='Extract an archive', aliases=['x'])
    x_parser.add_argument('gar', help='Path to a GAR archive')
    x_parser.set_defaults(func=gar_extract)

    l_parser = subparsers.add_parser('list', description='List files in an archive', aliases=['l'])
    l_parser.add_argument('gar', help='Path to a GAR archive')
    l_parser.add_argument('--name-only', action='store_true', help='Show only file names')
    l_parser.set_defaults(func=gar_list)

    c_parser = subparsers.add_parser('create', description='Create an archive', aliases=['c'])
    c_parser.add_argument('-n', '--default-alignment', type=lambda n: int(n, 0),
                          help='Set the default alignment for files. Defaults to 4.')
    c_parser.add_argument('dir', help='Directory to pack')
    c_parser.add_argument('dest', help='Destination archive')
    c_parser.set_defaults(func=gar_create)

    args = parser.parse_args()
    args.func(args)
