# Scattegories — PythonAnywhere Deployment Guide

## 1. Upload the project

Upload the `scattegories/` folder to your PythonAnywhere home directory,
e.g. `/home/yourusername/scattegories/`

## 2. Create a virtualenv (in PythonAnywhere Bash console)

```bash
mkvirtualenv scattegories --python=python3.10
pip install django
```

## 3. Set up the web app

1. Go to **Web** tab → **Add a new web app**
2. Choose **Manual configuration** → **Python 3.10**
3. Set the **Source code** directory to `/home/yourusername/scattegories`
4. Set the **Virtualenv** to `/home/yourusername/.virtualenvs/scattegories`

## 4. Configure WSGI

Edit the WSGI file (linked from the Web tab). Replace all content with:

```python
import os
import sys

path = '/home/yourusername/scattegories'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'scattegories.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Replace `yourusername` with your actual PythonAnywhere username.

## 5. Static files

In the Web tab, under **Static files**:
- URL: `/static/`
- Directory: `/home/yourusername/scattegories/staticfiles`

Then in Bash:
```bash
cd ~/scattegories
python manage.py collectstatic --noinput
```

## 6. Database setup

```bash
cd ~/scattegories
python manage.py migrate
python manage.py createsuperuser   # for /admin/ access
```

## 7. Update settings for production

In `scattegories/settings.py`, update:

```python
DEBUG = False
ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']
SECRET_KEY = 'your-long-random-secret-key-here'
```

## 8. Reload and test

Click **Reload** in the Web tab.

Visit:
- `https://yourusername.pythonanywhere.com/` — Player join screen
- `https://yourusername.pythonanywhere.com/lobby/` — Player lobby
- `https://yourusername.pythonanywhere.com/game/host/` — Host dashboard
- `https://yourusername.pythonanywhere.com/admin/` — Django admin

---

## Game flow

### Host
1. Go to `/game/host/` — log in as a player first (you're a player too)
2. Create a game
3. Optionally customise the 10 questions per round (or leave blank for defaults)
4. Click **Start New Round** — this picks a random letter
5. Click **Begin Timer** — players can now submit answers
6. Click **Lock Answers** when time is up (or wait for auto-expire)
7. Review answers question by question — ✅/❌ each one
8. Click **Confirm** to advance to the next question
9. After Q10, view the leaderboard
10. Repeat for up to 4 rounds

### Players
1. Go to the root URL `/`
2. Enter their name — UUID is remembered in localStorage
3. Wait on `/lobby/` — auto-redirects when round starts
4. Submit answers — auto-saved every ~800ms
5. Returns to lobby when round locks

---

## Architecture notes

- **Polling**: host view polls every 3s, player view every 2s. Fine for 20 players.
- **State authority**: all state transitions are server-only. Frontend never decides.
- **Scoring**: automated duplicate detection is advisory. Host ✅/❌ is final.
- **Jury votes**: ephemeral, never affect scoring, 15-second window.
- **Timezone**: Australia/Melbourne throughout.
