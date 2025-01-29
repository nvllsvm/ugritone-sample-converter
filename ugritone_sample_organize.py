#!/usr/bin/env python3
"""
Convert Ugritone samples to standard audio files.
"""
import argparse
import collections
import os
import pathlib
import subprocess
import tempfile


def join_flac(source1, source2, target, delete=False):
    with tempfile.NamedTemporaryFile(delete=False, dir=target.parent, suffix='.wav') as handle:
        temp_path = pathlib.Path(handle.name)
        subprocess.run(
            ['ffmpeg', '-y', '-i', f'concat:{source1}|{source2}', '-c', 'copy', temp_path],
            check=True)
        temp_path.rename(target)
        if delete:
            source1.unlink()
            source2.unlink()


def all_files(root):
    files = set()
    stack = []
    if root.is_file():
        files.add(root)
    else:
        stack.append(root)
    while stack:
        for path in stack.pop().iterdir():
            if path.is_dir():
                stack.append(path)
            else:
                files.add(path)
    return files


def safe_write_bytes(path, data):
    path = pathlib.Path(path)
    if isinstance(data, str):
        data = data.encode()
    with tempfile.NamedTemporaryFile(delete=False, dir=path.parent) as handle:
        temp_path = pathlib.Path(handle.name)
        try:
            temp_path.write_bytes(data)
            temp_path.rename(path)
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=pathlib.Path)
    parser.add_argument("-n", "--max-workers", type=int, default=os.cpu_count())
    parser.add_argument("--rm", action="store_true")
    args = parser.parse_args()

    all_inst = {}
    for path in all_files(args.path):
        if path.suffix != '.flac':
            continue
        if path.parents[0].name == 'Reverbs':
            continue
        path = path.relative_to(args.path)
        is_oneshot = any([p.name.lower() == 'oneshots' for p in path.parents])
        if is_oneshot:
            if len(list((args.path / path.parent).iterdir())) != 1:
                raise RuntimeError(path)
            continue
        else:
            round_robin_variation, velocity_group, midi_note_id, inst, chan = path.stem.split()
            all_inst.setdefault(path.parent, {})
            all_inst[path.parent].setdefault(inst, {})
            all_inst[path.parent][inst].setdefault(midi_note_id, set())
            all_inst[path.parent][inst][midi_note_id].add(chan)
        continue
        print(is_oneshot, path.name)
        num, name = path.parent.name.split(maxsplit=1)
        continue
        samples.setdefault(num, {})
        samples[num].setdefault(name, {})
        continue
    for parent in all_inst:
        for inst, midi_notes in all_inst[parent].items():
            all_channels = []
            for chan in midi_notes.values():
                all_channels.extend(chan)
            if len(all_channels) != len(set(all_channels)):
                print(parent, inst, midi_notes)
    print('done')




if __name__ == "__main__":
    main()
