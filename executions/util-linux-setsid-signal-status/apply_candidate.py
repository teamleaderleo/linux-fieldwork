from pathlib import Path
import sys

p = Path(sys.argv[1])
text = p.read_text()
old = '''\t\t\tif (WIFEXITED(status))\n\t\t\t\treturn WEXITSTATUS(status);\n\t\t\terr(status, _("child %d did not exit normally"), pid);\n'''
new = '''\t\t\tif (WIFEXITED(status))\n\t\t\t\treturn WEXITSTATUS(status);\n\t\t\tif (WIFSIGNALED(status))\n\t\t\t\treturn WTERMSIG(status) + 128;\n\t\t\twarnx(_("child %d did not exit normally"), pid);\n\t\t\treturn EXIT_FAILURE;\n'''
if text.count(old) != 1:
    raise SystemExit(f'wait-status anchor count={text.count(old)}')
p.write_text(text.replace(old, new, 1))
