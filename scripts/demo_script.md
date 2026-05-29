# Demo Script

1. Start the app:

   ```powershell
   python run.py
   ```

2. Open `http://127.0.0.1:8080`.

3. In `Workflows`, select `Customer Support Swarm` and run:

   ```text
   My order ORD-1024 is delayed and I want a refund.
   ```

4. Move to `Monitor` and show:

   - `run.queued`
   - `agent.started`
   - `agent.completed`
   - `run.completed`
   - token and cost counters

5. Move to `Channel` and send:

   ```text
   My order ORD-1024 is delayed. Can you help and refund me?
   ```

6. For the real Telegram demo:

   - Create a bot with Telegram `@BotFather`.
   - Set `ENABLE_TELEGRAM=true` and `TELEGRAM_BOT_TOKEN=<your token>`.
   - Restart `python run.py`.
   - Send the same order message to the bot and show the response in Telegram plus the persisted trace in the web UI.

7. In `Agents`, open `Triage Agent` and explain the configurable dimensions:

   - name
   - role
   - system prompt
   - model
   - tools
   - channels
   - schedules
   - memory
   - skills
   - interaction rules
   - guardrails
