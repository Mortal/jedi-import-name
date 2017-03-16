#!/usr/bin/env python3
import os
import argparse


IMPORT_TYPES = ('dotted_as_name', 'dotted_as_names', 'import_as_name',
                'import_as_names', 'import_from', 'import_name')


def imports(filename):
    import jedi

    for n in jedi.names(path=filename):
        node = n._name.tree_name
        if node.parent.type in IMPORT_TYPES:
            yield node


def make_import_statement(node):
    defined_name = str(node)

    def dotted_str(n):
        if n.type == 'dotted_name':
            return ''.join(map(str, n.children))
        else:
            return str(n)

    if node.parent.type == 'dotted_as_name':
        original = node.parent.children[0]
        original_as = '%s as ' % dotted_str(original)
    elif node.parent.type == 'import_as_name':
        original = node.parent.children[0]
        original_as = '%s as ' % dotted_str(original)
    else:
        original_as = ''

    import_stm = node.parent
    while import_stm.type not in ('import_name', 'import_from'):
        import_stm = import_stm.parent
    first_keyword = import_stm.get_first_leaf()
    if first_keyword == 'import':
        prefix = 'import '
    elif first_keyword == 'from':
        root = [first_keyword.get_next_leaf()]
        while root[-1].get_next_leaf() != 'import':
            root.append(root[-1].get_next_leaf())
        prefix = 'from %s import ' % ''.join(map(str, root))
    else:
        raise TypeError(first_keyword)
    return prefix + original_as + defined_name


def get_import_statements(filename, skip_errors=False, skip_relative=False,
                          skip_future=True):
    for node in imports(filename):
        try:
            line = make_import_statement(node)
            if skip_relative and line.startswith('from .'):
                continue
            if skip_future and line.startswith('from __future__ import '):
                continue
            yield line
        except Exception as exn:
            if not skip_errors:
                raise


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
    for line in lines:
        if line not in seen:
            print(line, flush=True)
            seen.add(line)
            if limit and len(seen) >= limit:
                break
    if not seen:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
