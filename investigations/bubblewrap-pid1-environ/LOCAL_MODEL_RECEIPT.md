# Local model receipt

Executed in the disposable analysis runner with:

```sh
FIELDWORK_MARKER=fieldwork-old-marker python3 repro_pid1_environ.py --model
```

Observed:

```text
clearenv: getenv=None proc_old=True proc_new=False
unsetenv: getenv=None proc_old=True proc_new=False
setenv: getenv='fieldwork-new-marker' proc_old=True proc_new=False
```

Environment at execution:

```text
Debian GNU/Linux 13 (trixie)
Linux 6.18.35 x86_64
Python 3.13.5
uid 0 in disposable runner
```

The marker is synthetic. The model demonstrates only the generic Linux/libc representation split; exact Bubblewrap runtime evidence is tracked separately.