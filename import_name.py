#!/usr/bin/env python3
import os
import argparse
from names import get_import_statements


def is_root(path: os.PathLike):
    return (os.path.abspath(path) == '/' or
            os.path.exists(os.path.join(path, '.git')))


def is_python_file(path: os.PathLike):
    return os.path.basename(path).endswith('.py') and not os.path.isdir(path)


def find_python_files_under(path: os.PathLike, skip=None):
    assert os.path.isdir(path)
    dirs = []
    skip_inode = skip and os.stat(skip).st_ino
    for child in os.scandir(path):
        if child.name.startswith('.'):
            continue
        if child.name == '__pycache__':
            continue
        if skip_inode and child.inode() == skip_inode:
            continue
        elif child.is_dir():
            dirs.append(child)
        elif is_python_file(child):
            yield child
    for d in dirs:
        yield from find_python_files_under(d)


def find_python_files_from(path: os.PathLike, skip=None):
    yield from find_python_files_under(path, skip)
    if not is_root(path):
        yield from find_python_files_under(os.path.join(path, '..'), path)


def get_imports_for_name(name, filenames, start, skip_relative):
    for filename in filenames:
        for line in get_import_statements(filename.path, skip_relative):
            if line.endswith(' ' + name):
                yield line


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--absolute', '-a', action='store_true',
                        help='do not output relative imports')
    parser.add_argument('--start', default='.',
                        help='directory or file to start search')
    parser.add_argument('--parents', action='store_true',
                        help='search parent directories for code')
    parser.add_argument('-n', type=int,
                        help='stop searching after this number of results')
    parser.add_argument('name', help='name to import')
    args = parser.parse_args()
    if os.path.isdir(args.start):
        start = args.start
    else:
        start = os.path.dirname(args.start)
    if args.parents:
        filenames = find_python_files_from(start)
    else:
        filenames = find_python_files_under(start)
    lines = get_imports_for_name(args.name, filenames, start, args.absolute)
    seen = set()
    limit = args.n
    for i, line in enumerate(lines):
        if line not in seen:
            print(line)
            seen.add(line)
            if limit and len(seen) >= limit:
                break


if __name__ == '__main__':
    main()
