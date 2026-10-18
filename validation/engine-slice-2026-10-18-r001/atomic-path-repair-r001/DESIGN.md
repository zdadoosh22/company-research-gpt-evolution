# Atomic long-path repair

Before editing, DEV tools/research_checkpoint.py and its checkpoint tests exactly matched installed originals. Existing DEV queue and amendment tests were left untouched.

The only production-code change replaces destination-name.UUID32.tmp with UUID32.tmp in the same destination directory. The random temporary basename is now 36 characters regardless of destination basename. Exclusive xb creation, output symlink rejection, write/flush/fsync, os.replace and final cleanup are unchanged. No backup, immutable event or archive logic changed.

The real-filesystem regression constructs a 240-character destination, below classic Windows MAX_PATH. The former temporary path is 277 characters; the new path is 236 characters. It verifies first creation and overwrite with actual os.replace, checking content, short random basename, identical directory and absence of temporary residue. A separate injected replacement failure occurs after verifying the completed staged file and old destination; it verifies the prior destination bytes survive and the temporary file is removed.

Focused checkpoint suite: 17 tests ran successfully, with one existing Windows symlink-creation test skipped because this environment does not grant symlink creation. Exact command, source hashes and installed-relative delta hash are in TEST-EVIDENCE.json. This validates the code repair, not successful archival of the actual sixth review. Parent owns checkpoints, source-bound full regression, installation and actual archive retry. No model calls or production state writes occurred in this task.
