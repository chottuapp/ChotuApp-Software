# ChotuApp software backup — 22 October 2026

This is a source-code snapshot and recovery handover, not a disk image or a complete conversation export. The archive root contains the entire tracked main-branch project at the commit recorded in repository-refs.json. This backup directory adds the installed-release APK, exact owner Rule 804, project instructions, source inventory, branch references and operational report snapshots. Existing historical spreadsheets, fixtures and archives tracked on main are retained.

## Continue in another ChatGPT account

Connect the chottuapp/ChotuApp-Software repository with appropriate access. Upload this document and HANDOVER.md. Ask the assistant to inspect the actual code and current reports before making changes. Chat memory and account access do not transfer merely by reconnecting GitHub. Never treat the report snapshots as current live status.

## Restore the software

1. Extract the ZIP; keep an untouched original backup.
2. Read AGENTS.md if present, backup/Rule-804-SKILL.md and docs/OPERATIONS_PREFERENCES.md. The owner overrides in HANDOVER.md supersede older defaults.
3. See requirements and setup documentation in the archive root; create a separate environment and run the appropriate tests before deployment.
4. Existing GitHub Actions workflows are under .github/workflows/. They need repository permissions and their original encrypted secrets; ZIP archives do not export GitHub secrets.
5. Android source, Gradle configuration and operational documentation are included. Read docs/ANDROID_APP.md, docs/KHAADI_ANDROID.md and docs/mobile-studio-release.md. The attached ChotuApp-Studio.apk is the existing signed release, not a newly built update.
6. To preserve additional report/data branches locally, run `python download-all-branches.py` inside this backup directory. This downloads every recorded remote branch at its immutable commit, including audit-held workbooks and rollback backups. It may require substantial disk space. The core ZIP does not duplicate all separate branch contents.

## Integrity and limits

SHA256SUMS.txt covers files added in this backup directory; source-tree-inventory.txt records every tracked source blob at the captured source revision. repository-refs.json lists immutable branch commits. Download the full ZIP, not just the APK.

Not included: GitHub/Google/AWS account access, Actions secret values, tokens, passwords, private APK signing key, phone/PC-only saved responses, expired Actions checkpoints, full chat transcript, or external Google Drive contents. These cannot be reconstructed from GitHub source. The repository has historical committed assets; this is not a claim of a full historical secret audit.

The stable Studio signing key must be kept in a separate encrypted private backup. Never upload it or service credentials to a public repository. Without that key a newly built APK cannot replace the existing installation using the same signature. The already-signed APK remains usable.
