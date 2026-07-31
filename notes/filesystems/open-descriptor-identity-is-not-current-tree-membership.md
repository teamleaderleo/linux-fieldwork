# Open descriptor identity is not current tree membership

An open file or directory descriptor keeps object identity across rename and
pathname replacement. That is exactly why descriptor-relative mutation prevents
symlink redirection.

It does not prove that the object still belongs to the operation tree.

For recursive filesystem operations, separate three claims:

1. **identity:** the descriptor still names the inode originally opened;
2. **membership:** following descriptor-relative `..` currently reaches the
   pinned operation root;
3. **authority:** the operation is still allowed to mutate that inode.

A current-membership check can reject an object that has already moved outside
the root. It cannot atomically bind the ancestry result to a later `futimes`,
write, chmod, chown, or removal. A move after the check remains possible.

Therefore choose and state one ownership model:

- open-time authority retained until operation completion;
- current-membership authority with an explicit residual race and failure mode;
- a quiescent-tree premise proved through process ownership;
- or no pre-output tree mutation.

Do not describe descriptor identity alone as containment. Do not add repeated
pathname checks and imply that they make a check/use pair atomic.
