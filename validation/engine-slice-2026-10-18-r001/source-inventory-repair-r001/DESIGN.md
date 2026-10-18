# Owned source inventory repair

DEV release source and release tests matched installed source byte-for-byte before editing. The only production-source change is research_release._source_files. Artifact allowlists and make_reference remain unchanged; no dependency content is copied. Earlier queue/checkpoint repairs and adapter tests are preserved.

## Traversal boundary

Explicit scandir recursion replaces rglob. Exact tools/node_modules is skipped before stat, resolution, symlink/junction inspection or descent. All other source paths are checked component-by-component for symlinks, Windows junctions and resolved paths outside the project before recursion or source selection. This includes the validation parent of validation/tests. Legitimate nested tools Python/PowerShell and nested tests Python remain included and sorted. Source-directory paths that unexpectedly name files are rejected.

The shared inventory contains 65 owned files in actual DEV. Generated dependency/runtime contents are outside owned-source scope. Their exclusion does not certify those dependencies: installed-client executable hash, selected capability-catalog hash and runtime restriction evidence remain separately pinned and assessed by existing runtime controls. Dependency-installation state is not implicitly accepted by this inventory.

## Regression capture successor

capture_regression-r002.py is a proposed successor, saved here only. Its snapshot calls the selected root's research_release._source_files rather than duplicating a traversal/exclusion policy. A local read-only invocation of snapshot matches the shared 65-file inventory exactly. The original dated capture script, old 131-file snapshots and failed release candidate remain untouched. The parent must integrate the reviewed source first and use a fresh output base; this task has not executed the successor's complete suite command.

## Evidence

13 focused release tests passed. New tests use a real generated vendor subtree and real nested owned Python/PowerShell/test files. A traversal guard fails if vendor content is entered; actual release validation accepts the owned manifest and then rejects nested-source tampering. Mocked nonvendor Windows junction, resolved escape and source-file symlink tests reject before external-directory descent or source binding. The mocked junction case is explicitly not real OS-link evidence; parent independently verifies the existing vendor junction against installed source.

TEST-EVIDENCE.json binds exact source/test/successor hashes, original capture hash, focused command/result and normalized installed-relative patch. owned-source-snapshot.json records the shared DEV source selection. No release pointer, original source, production state, preserved rejected candidate, model invocation or live gate changed. Parent owns checkpoints, complete source-bound regression, integration and release acceptance.
