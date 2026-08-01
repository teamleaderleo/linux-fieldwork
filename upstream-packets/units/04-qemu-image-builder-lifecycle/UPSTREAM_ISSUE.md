# Draft upstream issue

## Title

QEMU image builder can publish partial output and resume after signal cleanup

## Body

`mmdebstrap-autopkgtest-build-qemu` writes the caller-selected image pathname during filesystem creation and later mutates it with partition and FAT-copy steps. A failure after the initial write can therefore leave a partial object at the final name or replace an existing valid image before the command succeeds.

The script also uses the same cleanup-only trap for ordinary exit and INT, TERM, and QUIT. When a signal is delivered to the wrapper while it waits for a foreground operation, the trap can run after that operation returns, remove temporary files, return to normal control flow, and allow later image work to continue.

A proposed patch combines the lifecycle fixes:

- construct the image in a private sibling directory on the destination filesystem;
- route every image mutation to the private path;
- publish through one final rename;
- preserve existing output on ordinary failure and pre-publication signals;
- terminate HUP/INT/QUIT/TERM with statuses 129/130/131/143;
- run cleanup once with explicit result precedence;
- preserve a published image after a later signal;
- reject ambiguous trailing-slash destinations before temporary state is created.

The reduced regression covers existing and absent output, ordinary failure, wrapper-only HUP/INT/TERM, immediate reruns, successful publication and mode, TERM after publication, cleanup failure precedence, and path rejection.

Known limits: parent-only signals can remain deferred during a foreground wait; the patch adds no child forwarding, fsync durability, concurrent-publisher lock, image-content validation, or replaced-inode metadata policy.

This draft remains internal pending explicit authorization.
