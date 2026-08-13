from pathlib import Path
import sys

p = Path(sys.argv[1])
text = p.read_text()
old = '''\t\tif (WIFEXITED(status) &&\n\t\t    WEXITSTATUS(status) != EXIT_SUCCESS)\n\t\t\texit(WEXITSTATUS(status));\n'''
new = '''\t\tif (WIFEXITED(status)) {\n\t\t\tif (WEXITSTATUS(status) != EXIT_SUCCESS)\n\t\t\t\texit(WEXITSTATUS(status));\n\t\t} else if (WIFSIGNALED(status))\n\t\t\texit(WTERMSIG(status) + 128);\n\t\telse\n\t\t\texit(EXIT_FAILURE);\n'''
if text.count(old) != 1:
    raise SystemExit(f'waitchild anchor count={text.count(old)}')
p.write_text(text.replace(old, new, 1))
