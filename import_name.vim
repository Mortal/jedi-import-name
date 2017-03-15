" vim: set sw=4 et:
function ImportNameUnderCursorHandle(channel, msg)
    let msg = py3eval('insert_import(' . json_encode(a:msg) . ')')
    redraw
    echom msg
endfunction

function ImportNameUnderCursorStderr(channel, msg)
    echoe a:msg
endfunction

function ImportNameUnderCursorExit(job, status)
    if a:status != 0
        echoe 'import_name failed'
    else
        "echom 'import_name exited'
    endif
endfunction

function ImportNameUnderCursor()
    let args = ['import_name', '-n1', '--start', expand('%:p'), '--parents', '--absolute', expand('<cword>')]
    let opts = {'in_io': 'null', 'out_cb': 'ImportNameUnderCursorHandle', 'err_cb': 'ImportNameUnderCursorStderr', 'exit_cb': 'ImportNameUnderCursorExit'}
    let job = job_start(args, opts)
    let channel = job_getchannel(job)
    if ch_status(channel) != "open"
        echoe 'Could not start import_name'
    endif
    "echom 'Invoked import_name'
endfunction

py3 <<EOF
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
        return parse_lines(source_lines)
    except SyntaxError as exn:
        try:
            linenos = toplevel_linenos(source)
        except SyntaxError:
            # Syntax error in low-level parser (i.e. grammar error).
            # Linear search for longest best prefix.
            i = exn.lineno - 1
            while i > 0:
                try:
                    return parse_lines(source_lines[:i])
                except SyntaxError:
                    i -= 1
            # Syntax error on first line.
            return parse_lines(())
        else:
            # Sophisticated syntax error (not grammar error).
            # Use parser's line number info to skip top-level statement.
            exn_start = next(l for l in reversed(linenos)
                             if l <= exn.lineno)
            return parse_lines(source_lines[:exn_start-1])


def end_of_preamble(source_lines):
    tree = parse_until_syntax_error(source_lines)
    for child in tree.body:
        if child.__class__.__name__ not in ('Import', 'ImportFrom', 'Expr'):
            return child.lineno - 1
    return len(source_lines)


def insert_import(line):
    lineno = end_of_preamble(vim.current.buffer[:])
    while lineno > 0 and vim.current.buffer[lineno-1] == '':
        lineno -= 1
    vim.current.buffer[lineno:lineno] = [line]
    return "Inserted %r at line %s" % (line, lineno)
EOF
au FileType python nnoremap <buffer> <Leader>i :<C-u>call ImportNameUnderCursor()<CR>
