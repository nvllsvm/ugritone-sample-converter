#!/usr/bin/env python3
"""
Convert Ugritone samples to standard audio files.
"""
import argparse
import contextlib
import concurrent.futures
import os
import pathlib
import subprocess
import sys
import tempfile


def decode_flac(source, target):
    subprocess.run(
        ['flac', '--keep-foreign-metadata-if-present', '--silent', '-d', '-f', '-o', target, '--', source],
        check=True,
    )


def encode_flac(source, target):
    subprocess.run(
        ['flac', '--keep-foreign-metadata-if-present', '--silent', '--best', '--verify', '-f', '-o', target, '--', source],
        check=True,
    )


def join_wav(source1, source2, target):
    subprocess.run(
        ['sox', '--', source1, source2, target],
        check=True)


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


def _process_file(source_sta, source_stp, target, delete=True):
    with contextlib.ExitStack() as exit_stack:
        tmp_sta = exit_stack.enter_context(
            tempfile.NamedTemporaryFile(suffix='.wav'))
        decode_flac(source_sta, tmp_sta.name)

        tmp_stp = exit_stack.enter_context(
            tempfile.NamedTemporaryFile(suffix='.wav'))
        decode_flac(source_stp, tmp_stp.name)

        tmp_wav = exit_stack.enter_context(
            tempfile.NamedTemporaryFile(suffix='.wav'))
        join_wav(tmp_sta.name, tmp_stp.name, tmp_wav.name)

        tmp_flac = exit_stack.enter_context(
            tempfile.NamedTemporaryFile(suffix='.flac'))
        encode_flac(tmp_wav.name, tmp_flac.name)

        safe_write_bytes(target, pathlib.Path(tmp_flac.name).read_bytes())

    if delete:
        source_sta.unlink()
        source_stp.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=pathlib.Path)
    parser.add_argument("-n", "--max-workers", type=int, default=os.cpu_count())
    parser.add_argument("--rm", action="store_true")
    args = parser.parse_args()

    matches = {}
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=args.max_workers) as executor:
        for path in all_files(args.path):
            if not path.name.lower().endswith('.ugrisample.flac'):
                continue
            name = str(path.parent / path.name.removesuffix('.ugrisample.flac')).strip()
            if name.endswith('STA'):
                key = 'STA'
                name = name.removesuffix('STA').strip()
            elif name.endswith('STP'):
                key = 'STP'
                name = name.removesuffix('STP').strip()
            else:
                raise ValueError(name)
            matches.setdefault(name, {})
            if key in matches[name]:
                raise ValueError
            matches[name][key] = path

        for k, v in matches.items():
            if set(v) != {'STA', 'STP'}:
                raise ValueError(k)

        future_to_paths = {}
        for name, parts in matches.items():
            target = pathlib.Path(name + '.flac')
            if target.exists():
                continue
            future = executor.submit(
                _process_file, parts['STA'], parts['STP'], target, True)
            future_to_paths[future] = target

        errors = []
        num_printed = 0
        for future in concurrent.futures.as_completed(future_to_paths):
            target = future_to_paths[future]
            try:
                future.result()
            except Exception as e:
                errors.append(e)
                msg = f"ERROR: {target}"
            else:
                msg = f"Success: {target}"
            num_printed += 1
            print("({}/{})\t{}".format(
                str(num_printed).rjust(len(str(len(future_to_paths)))),
                len(future_to_paths),
                msg,
            ))
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            sys.exit(1)



if __name__ == "__main__":
    main()
