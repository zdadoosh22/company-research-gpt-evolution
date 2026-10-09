# Connect the ordinary Chat companion and prove access

9 October 2026. The repository exists and local publication was verified. **Access from the separate ordinary Chat project has not been demonstrated.** Local Git Credential Manager/API access is different from the Chat GitHub plugin connection.

1. In ChatGPT, open **Plugins**, find **GitHub**, and install/enable it if needed. If it is already installed, open its connection settings. Complete **Connect GitHub** / authentication when prompted using the account that owns `zdadoosh22/company-research-work`. The exact authentication prompt can appear during installation or first use. Do not create/import a plugin marketplace for this research repository; it is a source repository, not a custom plugin.
2. When GitHub asks about repository access, use **Only select repositories** and include **company-research-work**. If changing an existing installation, preserve its other selected repositories rather than replacing their selection. Add this repository through the relevant GitHub application shown by the plugin's authentication flow. Do not assume a Codex-specific application or a different connection automatically grants ordinary Chat access.
3. For an existing installation, open GitHub **Settings → Applications → Installed GitHub Apps**, choose **Configure** for that relevant application, add this repository under **Repository access**, and save. Direct settings page: https://github.com/settings/installations . If GitHub requires reauthentication or organisational approval, complete that specific request; do not send credentials to Chat or Work.
4. Open a **new ordinary Chat** inside **Company Research - review and planning** after the plugin is installed/enabled. Use **@GitHub** if available, or explicitly ask for the GitHub plugin. Send the saved CHAT-STARTER-MESSAGE.txt; it names the verified full publishing commit.
5. Require actual tool retrieval at that full commit: the package's ACCESS-CHECK.txt, validation/repository-identity.json, methodology/current.json, CHAT-HANDOFF.md, REVIEW-EVIDENCE.md and REFERENCE-UPDATE.txt. Chat must return the access-check challenge ID, project identity/version/hash and citations or tool-derived repository links. The challenge ID is not included in the starter message or upload copies. Check it against the local ACCESS-CHECK.txt. A paraphrase of the uploaded files does not prove GitHub access.
6. If the plugin cannot retrieve the repository or pin the revision, its access test fails. Ask it to state which step failed; check the selected account, installed application and repository selection. If access remains unavailable, supply the three precisely named text files below as dated attachments. Chat can plan from those copies but must not claim verified GitHub access. No paid service or private repository made public is required by this procedure.

## Exact source files and instructions

For durable project Sources or an access-failure fallback, upload **CHAT-HANDOFF.md**, **REVIEW-EVIDENCE.md** and **REFERENCE-UPDATE.txt** from this handoff directory. Paste **CHAT-PROJECT-INSTRUCTIONS-REPLACEMENT.txt** into the project's instructions field. If GitHub access succeeds, Chat can retrieve these exact files instead; no full-project upload is needed. SOURCE-MANIFEST.json is optional for machine-readable binding checks.

No credentials, operational databases, raw checkpoint JSON, account quota records or private broker data are needed. Relevant issuer PDF filenames and hashes are listed in REVIEW-EVIDENCE.md for a later targeted visual review only if actually necessary.

## Official documentation used

- OpenAI, [Plugins](https://learn.chatgpt.com/docs/plugins): Plugins tab, install/connect, new chat and explicit invocation. This establishes the general supported workflow, not your account's successful GitHub connection or availability.
- GitHub, [Reviewing and modifying installed GitHub Apps](https://docs.github.com/en/apps/using-github-apps/reviewing-and-modifying-installed-github-apps): repository access selection and saving an existing application's configuration.

The repository/setup stage is complete independently of this remaining user-side Chat connection test. Work must inspect Chat's proposed next assignment against actual project/goal state before executing it. This guide creates no new research goal.
