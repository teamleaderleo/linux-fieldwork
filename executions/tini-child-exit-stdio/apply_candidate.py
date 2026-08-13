from pathlib import Path
import sys

p = Path(sys.argv[1])
text = p.read_text()
replacements = {
'''\t\tif (isolate_child()) {\n\t\t\treturn 1;\n\t\t}\n''': '''\t\tif (isolate_child()) {\n\t\t\t_exit(1);\n\t\t}\n''',
'''\t\tif (restore_signals(sigconf_ptr)) {\n\t\t\treturn 1;\n\t\t}\n''': '''\t\tif (restore_signals(sigconf_ptr)) {\n\t\t\t_exit(1);\n\t\t}\n''',
'''\t\tPRINT_FATAL("exec %s failed: %s", argv[0], strerror(errno));\n\t\treturn status;\n''': '''\t\tPRINT_FATAL("exec %s failed: %s", argv[0], strerror(errno));\n\t\t_exit(status);\n''',
}
for old, new in replacements.items():
    if text.count(old) != 1:
        raise SystemExit(f'anchor count={text.count(old)} for {old!r}')
    text = text.replace(old, new, 1)
if text.count('_exit(') != 3:
    raise SystemExit(f'_exit count={text.count("_exit(")}, want 3')
p.write_text(text)
