"""
Diamantové drby — digitální verze
Webová aplikace pro cca 10 týmů hrajících současně na vlastních zařízeních.
Server je autoritativní zdroj pravdy (otázky, čas, skóre) — klient jen
zobrazuje a odesílá volby. Stejný princip jako předchozí hry (raketa,
hvězda), jen s bulvárními/drbnovskými otázkami a diamantovým přívěskem
jako výslednou kresbou.
"""
import json, os, time, uuid, hashlib, random
from flask import Flask, request, session, jsonify, render_template, redirect, url_for

from geometry import diamond_points, wrong_points

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
QUESTIONS_PATH = os.path.join(DATA_DIR, "questions.json")
TEAMS_PATH = os.path.join(DATA_DIR, "teams.json")
os.makedirs(DATA_DIR, exist_ok=True)  # teams.json is created on first save — no need to upload an empty one

with open(QUESTIONS_PATH, encoding="utf-8") as f:
    QUESTIONS = json.load(f)

N = len(QUESTIONS)
DIAMOND_PTS = diamond_points(N)
WRONG_PTS = wrong_points(DIAMOND_PTS)

TIME_LIMIT = 20      # seconds for full speed bonus window
BASE_SCORE = 100
BONUS_MAX = 50

app = Flask(__name__)
# Stable secret (not regenerated per process start) so a free-tier host's
# cold-start/restart mid-event doesn't silently log every team out.
app.secret_key = os.environ.get("SECRET_KEY", "diamantove-drby-2026-static-key")

TEAMS = {}  # team_id -> dict, in-memory + persisted to disk
# NOTE: state lives in this process's memory. Run with exactly ONE worker
# process (see Procfile: --workers 1, --threads N is fine) — multiple
# worker *processes* would each have their own empty TEAMS dict and teams
# would randomly "disappear" depending on which worker handled a request.


def save_teams():
    try:
        with open(TEAMS_PATH, "w", encoding="utf-8") as f:
            json.dump(TEAMS, f, ensure_ascii=False, indent=1)
    except Exception as e:
        print("warn: could not persist teams.json:", e)


def load_teams():
    global TEAMS
    if os.path.exists(TEAMS_PATH):
        try:
            with open(TEAMS_PATH, encoding="utf-8") as f:
                TEAMS = json.load(f)
        except Exception:
            TEAMS = {}


load_teams()


def option_map_for(team_id, idx):
    """Deterministic per-team shuffle of which side ('left'/'right') shows
    option 'a' vs 'b', so the true/false pattern can't be memorised across
    teams or guessed question-to-question."""
    h = hashlib.sha256(f"{team_id}:{idx}".encode()).hexdigest()
    flip = int(h[:8], 16) % 2 == 0
    return {"left": "a", "right": "b"} if flip else {"left": "b", "right": "a"}


def get_team():
    tid = session.get("team_id")
    if not tid or tid not in TEAMS:
        return None
    return TEAMS[tid]


@app.route("/")
def join_page():
    return render_template("join.html")


@app.route("/api/join", methods=["POST"])
def api_join():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()[:40]
    if not name:
        return jsonify({"error": "Zadejte název týmu."}), 400
    tid = uuid.uuid4().hex[:10]
    TEAMS[tid] = {
        "id": tid,
        "name": name,
        "created_at": time.time(),
        "idx": 0,
        "answers": [],
        "q_started_at": None,
        "finished": False,
        "finished_at": None,
        "total_score": 0,
        "total_time": 0,
    }
    save_teams()
    session["team_id"] = tid
    return jsonify({"ok": True, "team_id": tid, "name": name})


@app.route("/play")
def play_page():
    if not get_team():
        return redirect(url_for("join_page"))
    return render_template("play.html")


def current_rank(team_id):
    """Provisional rank of a team among ALL teams that have joined so far
    (finished or still playing), based on points earned up to this moment.
    This is a live/informal standing shown to a team while it is still
    playing — not the same as the final /board ranking, which only lists
