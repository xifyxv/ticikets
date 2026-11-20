# Jeff Tweaks Ticket Bot (Railway)

Discord ticket bot for **JEFF TWEAKS | TICKET CENTRE**.

- Purchase & Support buttons
- Tickets created in category `1572673615802011748`
- Panel posts to channel `1565079109225283644`
- Server ID: `1464708562046419172`

## Deploy to Railway (24/7)

1. Create a new GitHub repository and upload these files:
   - `bot.py`
   - `requirements.txt`
   - `Procfile`
   - `.gitignore`

2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo.

3. In your Railway project → Variables, add:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```

4. Railway will automatically detect the Python app and start it with `python bot.py`.

5. Once deployed, in Discord run:
   ```
   /setup-tickets
   ```

## Local testing (optional)

```bash
pip install -r requirements.txt
set DISCORD_TOKEN=your_token_here
python bot.py
```

## Notes
- Make sure the bot has **Manage Channels** permission.
- Create a role named **Staff** for ticket management.
- The bot stays online as long as the Railway service is running.
