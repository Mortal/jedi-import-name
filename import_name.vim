" vim: set sw=4 et:
function ImportNameUnderCursorHandle(channel, msg)
    let msg = py3eval('insert_import(' . json_encode(a:msg) . ')')
    redraw
    echom msg
endfunction

function ImportNameUnderCursorStderr(channel, msg)
    echoe a:msg
endfunction

function ImportNameUnderCursorExit(word, status)
    if a:status == 1
        redraw
        echom 'Could not find an import of ' . json_encode(a:word)
    elseif a:status != 0
        redraw
        echoe 'import_name failed'
    endif
endfunction

function ImportNameUnderCursor()
    let word = py3eval('get_importable_under_cursor()')
    if word == v:none
        return
    endif
    let args = ['import_name', '-n1', '--start', expand('%:p'), '--parents', '--absolute', word]
    let opts = {'in_io': 'null',
                \'out_cb': 'ImportNameUnderCursorHandle',
                \'err_cb': 'ImportNameUnderCursorStderr',
                \'exit_cb': {j, status -> ImportNameUnderCursorExit(word, status)}}
    let job = job_start(args, opts)
    let channel = job_getchannel(job)
    if ch_status(channel) != "open"
        echoe 'Could not start import_name'
    endif
    "echom 'Invoked import_name'
endfunction

py3 <<EOF
def get_script(source=None, column=None):
    # From jedi_vim.py
    import jedi
    jedi.settings.additional_dynamic_modules = \
        [b.name for b in vim.buffers if b.name is not None and b.name.endswith('.py')]
    if source is None:
        source = '\n'.join(vim.current.buffer)
    row = vim.current.window.cursor[0]
    if column is None:
        column = vim.current.window.cursor[1]
    buf_path = vim.current.buffer.name
    encoding = vim.eval('&encoding') or 'latin1'
    return jedi.Script(source, row, column, buf_path, encoding)


def get_dotted_name_until(leaf):
    leaves = [leaf]
    while True:
        dot = leaves[-1].get_previous_leaf()
        if dot != '.':
            break
        name = dot.get_previous_leaf()
        if name is None or name.type != 'name':
            return
        leaves.append(dot)
        leaves.append(name)
    return ''.join(map(str, reversed(leaves)))


def get_importable_under_cursor():
    script = get_script()
    module_node = script._get_module_node()
    leaf = module_node.name_for_position(script._pos)
    if leaf is None:
        vim.command(
            'echohl ErrorMsg | echo "No name under cursor" | echohl None')
        return
    name = get_dotted_name_until(leaf)
    if name is None:
        vim.command('echohl ErrorMsg | echo "Not something I can import" | ' +
                    'echohl None')
        return
    return name


def toplevel_linenos(source):
    import parser
    st = parser.suite(source)
    suite = parser.st2list(st, line_info=True)
    linenos = []
    for toplevel in suite[1:]:
        leaf = toplevel
        while isinstance(stm[1], list):
            # Not a leaf
            leaf = leaf[1]
        linenos.append(leaf[2])
    return linenos


def parse_lines(lines):
    import ast
    return ast.parse('\n'.join(lines) + '\n')


def parse_until_syntax_error(source_lines):
    try:
        return parse_lines(source_lines), len(source_lines)
    except SyntaxError as exn:
        try:
            linenos = toplevel_linenos('\n'.join(source_lines))
        except SyntaxError:
            # Syntax error in low-level parser (i.e. grammar error).
            # Linear search for longest best prefix.
            i = exn.lineno - 1
            while i > 0:
                try:
                    return parse_lines(source_lines[:i]), i
                except SyntaxError:
                    i -= 1
            # Syntax error on first line.
            return parse_lines(()), 0
        else:
            # Sophisticated syntax error (not grammar error).
            # Use parser's line number info to skip top-level statement.
            exn_start = next(l for l in reversed(linenos)
                             if l <= exn.lineno)
            return parse_lines(source_lines[:exn_start-1]), exn_start-1


def end_of_preamble(source_lines):
    tree, line_count = parse_until_syntax_error(source_lines)
    for child in tree.body:
        if child.__class__.__name__ not in ('Import', 'ImportFrom', 'Expr'):
            return child.lineno - 1
    return line_count


def insert_import(line):
    cur_line = vim.current.window.cursor[0] - 1
    lineno = end_of_preamble(vim.current.buffer[:cur_line])
    while lineno > 0 and vim.current.buffer[lineno-1] == '':
        lineno -= 1
    vim.current.buffer[lineno:lineno] = [line]
    return "Inserted %r at line %s" % (line, lineno + 1)
EOF
au FileType python nnoremap <silent> <buffer> <Leader>i :<C-u>call ImportNameUnderCursor()<CR>
