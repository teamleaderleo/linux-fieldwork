from pathlib import Path
import sys

p = Path(sys.argv[1])
text = p.read_text()
start_marker = '        // Accept the connection and get the socket\n'
end_marker = '        Ok(())\n    }\n\n    /// Dispatches a migration.\n'
if text.count(start_marker) != 1 or text.count(end_marker) != 1:
    raise SystemExit(
        f'anchors start={text.count(start_marker)} end={text.count(end_marker)}'
    )
start = text.index(start_marker)
end = text.index(end_marker, start)
block = text[start:end]
failed_event = '                event!("vm", "migration-receive-failed");\n'
if block.count(failed_event) != 1:
    raise SystemExit(f'failed-event owner count={block.count(failed_event)}')
block = block.replace(failed_event, '', 1)
indented = ''.join('    ' + line if line.strip() else line for line in block.splitlines(True))
replacement = (
    '        let receive_result: result::Result<(), MigratableError> = (|| {\n'
    + indented
    + '            Ok(())\n'
    + '        })();\n\n'
    + '        if receive_result.is_err() {\n'
    + '            event!("vm", "migration-receive-failed");\n'
    + '        }\n\n'
    + '        receive_result\n'
)
text = text[:start] + replacement + text[end + len('        Ok(())\n'):]
p.write_text(text)
