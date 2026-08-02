# Setup and operation

These steps assume you have completed the one-time developer setup in [developers.MD](developers.MD) (virtualenv, dependencies, `settings.toml`, and `pip install -e .`).

## 1. Configure the Hue bridge

1. Install the Philips Hue app on a phone or tablet on the **same Wi‑Fi network** as the bridge.
2. In the app, open **Settings → Hue bridges** and note the bridge IP address.
3. Add the IP and light index to `settings.toml` in the project root:

   ```toml
   light_ip = "192.168.1.100"
   light_number = 0
   hue_gamut = "C"
   ```

   Use `hue_gamut = "B"` for older A19 bulbs if colors look wrong.

If you move the bridge to a new network, update `light_ip` and re-pair — see [changed_location.MD](../changed_location.MD).

## 2. Install and start Redis

On macOS with Homebrew:

```bash
brew install redis
redis-server
```

Leave Redis running in its own terminal.

## 3. Load the color palette

**First time** (wipes Redis and loads the full palette):

```bash
python -m hue_sms.cli.load_palette
```

**Later updates** (add new colors without losing usage stats):

```bash
python -m hue_sms.cli.sync_palette
```

To refresh from the Wikipedia Crayola scraper:

```bash
python -m hue_sms.generate_colors.scrape_colors
python -m hue_sms.cli.adjust_palette   # optional: tune for your bulb gamut
python -m hue_sms.cli.sync_palette --refresh   # update RGB values in Redis
```

See [developers.MD](developers.MD) for details on scraping, gamut adjustment, and excluded colors.

## 4. Expose the SMS server with ngrok

Twilio needs a public URL to reach your Flask server.

1. Download ngrok from [ngrok.com/download](https://ngrok.com/download).
2. Start a tunnel to port 5000:

   ```bash
   ./ngrok http 5000
   ```

3. Copy the **Forwarding** HTTPS URL (e.g. `https://abc123.ngrok-free.app`).

## 5. Configure Twilio

1. Create a Twilio account and get a phone number.
2. Under **Phone Numbers → your number → Messaging**, set the webhook to your ngrok URL plus the Flask route (typically the root `/` or whatever route handles incoming SMS in `hue_flask.py`).
3. Set the webhook method to **HTTP GET** (matches the current Flask handler).

Add the Twilio number to `settings.toml` if you want it on the kiosk:

```toml
sms_phone_display = "555-123-4567"
```

## 6. Run the services

Open separate terminals (with the virtualenv activated):

```bash
# SMS server — press the Hue bridge button when the server first connects
python -m hue_sms.web.hue_flask
```

```bash
# Kiosk display — open full-screen on the window-facing monitor
python -m hue_sms.web.kiosk_display
```

Then open **http://127.0.0.1:8000** in a browser and enter full-screen mode.

The analytics dashboard (`plotlydash.py`) is optional and can run alongside or instead of the kiosk if you only need usage charts.

## 7. Verify everything is healthy

```bash
curl http://127.0.0.1:5000/health   # SMS server + Hue bridge + Redis
curl http://127.0.0.1:8000/api/health
```

Both should return `"ok": true` when all services are connected.

## Testing without SMS

Send a GET request to the Flask webhook the same way Twilio would:

```bash
curl "http://127.0.0.1:5000/?Body=sky%20blue"
```

Try a few colors and watch the kiosk spotlight update:

```bash
curl "http://127.0.0.1:5000/?Body=magenta"
curl "http://127.0.0.1:5000/?Body=goldenrod"
```

Special keywords: `random`, `next` (cycle), and hex codes like `#FF2A45`.

## Raspberry Pi / kiosk autostart

For a dedicated display machine, run `python -m hue_sms.web.hue_flask` and `python -m hue_sms.web.kiosk_display` as systemd services and launch Chromium in kiosk mode on boot. Point the browser at `http://127.0.0.1:8000`.

Typical approach:

1. Create systemd unit files for both Python services (run from the project venv, `WorkingDirectory` set to the repo root).
2. Enable them: `sudo systemctl enable --now hue-flask kiosk-display`.
3. Add a desktop autostart entry that runs Chromium with `--kiosk http://127.0.0.1:8000`.

Exact unit files depend on your Pi OS and install path — adapt paths to where you cloned the repo.

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Flask cannot reach the bridge | Confirm `light_ip` in `settings.toml`, same network, press bridge button while starting the SMS server |
| Color not recognized | Check Redis has the palette (`python -m hue_sms.cli.load_palette` or `sync_palette`); try a vivid color like "sky blue" |
| Color rejected as unsupported | Blacks, grays, whites, and muted browns are excluded by design |
| Kiosk shows stale state | Confirm Redis is running and the SMS server is up; check `/health` on both ports |
| Twilio webhook fails | ngrok tunnel must be running; URL must match Twilio config; use GET not POST |
