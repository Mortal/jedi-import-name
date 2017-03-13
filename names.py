#!/usr/bin/env python3
import os
import argparse
import sys
sys.path.append('/home/rav/.vim/bundle/jedi-vim/jedi')
from jedi import names


def dotted_name_str(n):
    children = n if isinstance(n, list) else getattr(n, 'children', (n,))
    return ''.join(str(c) for c in children)


IMPORT_TYPES = ('dotted_as_name', 'dotted_as_names', 'import_as_name',
                'import_as_names', 'import_from', 'import_name')


def imports(filename):
    for n in names(path=filename):
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


def get_import_statements(filename, skip_errors=False, skip_relative=False, skip_future=True):
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
        for line in get_import_statements(filename, skip_relative=args.absolute):
            print(line)


if __name__ == '__main__':
    main()
