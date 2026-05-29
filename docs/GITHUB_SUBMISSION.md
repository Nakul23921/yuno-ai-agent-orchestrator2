# GitHub Submission Guide

Use these steps to publish the project to your GitHub account.

## Option A: GitHub Desktop

1. Install GitHub Desktop from `https://desktop.github.com/`.
2. Open GitHub Desktop.
3. Choose `File -> Add local repository`.
4. Select:

   ```text
   C:\Users\nakul\Documents\Codex\2026-05-24\files-mentioned-by-the-user-yuno
   ```

5. If it asks to create a repository, accept.
6. Commit all files with a message:

   ```text
   Initial Yuno AI agent orchestration platform
   ```

7. Click `Publish repository`.
8. Keep it public unless the Yuno instructions say private is allowed.
9. Copy the GitHub repository URL and submit that link.

## Option B: Command Line

From PowerShell:

```powershell
cd C:\Users\nakul\Documents\Codex\2026-05-24\files-mentioned-by-the-user-yuno
git init
git add .
git commit -m "Initial Yuno AI agent orchestration platform"
```

Create an empty GitHub repository in your browser. Then connect and push:

```powershell
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

## Suggested Repository Name

```text
yuno-ai-agent-orchestrator
```

## What To Put In The Submission Email/Form

Use this format:

```text
Hi Yuno AI Team,

Please find my Round 0 submission here:
GitHub: https://github.com/<your-username>/yuno-ai-agent-orchestrator
Demo video: <loom/youtube/google-drive-link>

The project includes a local-first AI agent orchestration platform with a custom async runtime, web UI, SQLite persistence, two workflow templates, live monitoring, token/cost tracking, and Telegram integration.

Thanks,
Nakul
```

## Before Submitting

Run:

```powershell
python -m unittest discover -s tests
```

Then record a short demo showing:

- App startup
- Web UI
- Agent registry
- Workflow execution
- Monitor logs
- Channel simulator
- Real Telegram conversation if configured

