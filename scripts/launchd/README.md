# CT Maps Watchdog – launchd (macOS)

Run the CT Maps watchdog as a user LaunchAgent so backend and frontend start at login and restart automatically if they crash.

## Setup

1. **Edit the plist** if your project is not at `/Users/jacobmermelstein/Desktop/CT Maps`:
   - Open `ct-maps-watchdog.plist` and replace that path with your project root in:
     - `WorkingDirectory`
     - `StandardOutPath`
     - `StandardErrorPath`

2. **Copy to LaunchAgents:**
   ```bash
   cp scripts/launchd/ct-maps-watchdog.plist ~/Library/LaunchAgents/
   ```

3. **Load the agent:**
   ```bash
   launchctl load ~/Library/LaunchAgents/ct-maps-watchdog.plist
   ```

After login, the watchdog will start and keep backend (port 8000) and frontend (port 3000) running. Open http://localhost:3000.

## Unload / stop

```bash
launchctl unload ~/Library/LaunchAgents/ct-maps-watchdog.plist
./scripts/stop_all.sh
```

## Logs

- Watchdog output: `logs/watchdog.log`
- launchd stdout: `logs/watchdog-launchd.log`
- launchd stderr: `logs/watchdog-launchd.err.log`
