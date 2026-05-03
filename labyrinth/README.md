# Labyrinth – Django Board Game

A full implementation of the Labyrinth board game using Django + Vanilla JS.

## Setup

```bash
# 1. Install dependencies
pip install django

# 2. Apply migrations
python manage.py migrate

# 3. Replace placeholder images
#    Copy your real assets into: static/images/
#      - shapei.png, shapel.png, shapet.png  (512x512 base tiles)
#      - character01.png … character37.png   (512x512 character overlays)

# 4. Run the server
python manage.py runserver
```

Then open http://127.0.0.1:8000/ in your browser.

## Project Structure

```
labyrinth_game/
├── game/
│   ├── models.py       ← Game model, BFS, push logic
│   ├── views.py        ← All views + JSON API endpoints
│   ├── urls.py
│   └── migrations/
├── labyrinth/
│   ├── settings.py
│   └── urls.py
├── templates/
│   └── game/
│       ├── index.html  ← Landing / player-count selector
│       └── board.html  ← Main game board
├── static/
│   └── images/         ← ← Put your PNG assets here
└── manage.py
```

## Game Rules Implemented

- **7×7 grid** with 16 fixed tiles and 33 movable tiles + 1 spare
- **Push phase**: rotate spare → click arrow to push into movable row/col
- **Move phase**: BFS highlights reachable tiles; click to move token
- **Anti-undo rule**: cannot immediately reverse the previous push
- **Token wrapping**: players on a pushed-out tile wrap to the opposite side
- **2–4 players** supported; 24 of 37 characters randomly assigned each game

## API Endpoints

| Method | URL | Action |
|--------|-----|--------|
| GET    | `/` | Landing page |
| POST   | `/new/` | Start new game |
| GET    | `/<id>/` | Board view |
| GET    | `/<id>/state/` | JSON game state |
| POST   | `/<id>/rotate-spare/` | Rotate spare tile |
| POST   | `/<id>/push/` | Push tile (body: `{direction, index}`) |
| POST   | `/<id>/move/` | Move player (body: `{player_id, row, col}`) |
