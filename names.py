#!/usr/bin/env python3
import os
import argparse

from import_name import get_import_statements


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--absolute', '-a', action='store_true')
    parser.add_argument('filename')
    args = parser.parse_args()
    if os.path.isdir(args.filename):
        filenames = (os.path.join(root, filename)
                     for root, dirs, files in os.walk(args.filename)
                     for filename in files
                     if filename.endswith('.py'))
    else:
        filenames = (args.filename,)
    for filename in filenames:
        lines = get_import_statements(filename, skip_relative=args.absolute)
        for line in lines:
            print(line)


if __name__ == '__main__':
    main()
