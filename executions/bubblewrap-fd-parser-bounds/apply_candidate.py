from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
text = p.read_text()

include_anchor = '#include <ctype.h>\n'
if text.count(include_anchor) != 1:
    raise SystemExit(f'include anchor count={text.count(include_anchor)}')
text = text.replace(include_anchor, include_anchor + '#include <errno.h>\n#include <limits.h>\n', 1)

helper_anchor = 'static void\nparse_args_recurse (int          *argcp,\n'
if text.count(helper_anchor) != 1:
    raise SystemExit(f'helper anchor count={text.count(helper_anchor)}')
helper = '''static int\nparse_fd (const char *value)\n{\n  char *endptr = NULL;\n  long parsed;\n\n  errno = 0;\n  parsed = strtol (value, &endptr, 10);\n  if (value[0] == 0 || endptr[0] != 0 || errno == ERANGE || parsed < 0 || parsed > INT_MAX)\n    die ("Invalid fd: %s", value);\n\n  return (int) parsed;\n}\n\n'''
text = text.replace(helper_anchor, helper + helper_anchor, 1)

# Every current FD-valued option uses one of these local names and the same
# validation block. UID/GID and unrelated integer parsing use different names
# and error messages, so this replacement stays within the FD domain.
for var in ('the_fd', 'file_fd', 'src_fd'):
    text = text.replace(f'          int {var};\n          char *endptr;\n', f'          int {var};\n')

pattern = re.compile(
    r'(?P<indent> +)(?P<var>the_fd|file_fd|src_fd) = strtol \(argv\[1\], &endptr, 10\);\n'
    r'(?P=indent)if \(argv\[1\]\[0\] == 0 \|\| endptr\[0\] != 0 \|\| (?P=var) < 0\)\n'
    r'(?P=indent)  die \("Invalid fd: %s", argv\[1\]\);\n'
)

def repl(m):
    return f"{m.group('indent')}{m.group('var')} = parse_fd (argv[1]);\n"

text, count = pattern.subn(repl, text)
if count != 15:
    raise SystemExit(f'FD parser replacements={count}, want 15')
if 'die ("Invalid fd: %s", argv[1]);' in text:
    raise SystemExit('manual FD parser remains')
if text.count('parse_fd (argv[1]);') != 15:
    raise SystemExit('unexpected shared parser call count')

p.write_text(text)
