from flask import Flask, jsonify, request, render_template, send_from_directory
from threading import Lock
import time

app = Flask(__name__)
lock = Lock()

state = {
    "robot1": "AMARILLO", "robot2": "MORADO",
    "robot1_image": "/R_Amarillo.png", "robot2_image": "/R_Morado.png",
    "battle_number": 1,
    "attacks1": 0, "attacks2": 0,
    "status": "PREPARADOS PARA LA BATALLA",
    "elapsed_seconds": 0, "started_at": None,
    "winner": "", "reason": "", "phase": "ready"
}

def snapshot():
    data = dict(state)
    if data["phase"] == "running" and data["started_at"] is not None:
        data["elapsed_seconds"] = int(time.time() - data["started_at"])
    return data

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/attacks/<int:robot>")
def attacks_page(robot):
    if robot not in (1, 2):
        return jsonify({"error": "Robot inválido"}), 404
    return render_template("attacks.html", robot=robot)

@app.get("/<path:filename>")
def assets(filename):
    allowed = {"Fondo.jpg", "Fondo_Ganar.jpg", "Fondo_Proxima.jpg", "No_Batalla.png", "R_Amarillo.png", "R_Morado.png", "R_Rojo.png", "R_Verde.png", "videoplayback.m4a", "audio_final.m4a"}
    if filename not in allowed:
        return jsonify({"error": "Recurso no encontrado"}), 404
    return send_from_directory(app.root_path, filename)

@app.get("/api/state")
def get_state():
    with lock:
        return jsonify(snapshot())

@app.post("/api/attack/<int:robot>")
def add_attack(robot):
    if robot not in (1, 2):
        return jsonify({"error": "Robot inválido"}), 400
    with lock:
        if state["phase"] != "running":
            return jsonify({"error": "Solo se pueden registrar ataques durante una batalla en curso"}), 409
        key = "attacks1" if robot == 1 else "attacks2"
        state[key] += 1
        return jsonify(snapshot())

@app.post("/api/attack/<int:robot>/decrement")
def remove_attack(robot):
    if robot not in (1, 2):
        return jsonify({"error": "Robot inválido"}), 400
    with lock:
        if state["phase"] != "running":
            return jsonify({"error": "Solo se pueden corregir ataques durante una batalla en curso"}), 409
        key = "attacks1" if robot == 1 else "attacks2"
        state[key] = max(0, state[key] - 1)
        return jsonify(snapshot())

@app.post("/api/config")
def configure():
    payload = request.get_json(silent=True) or {}
    with lock:
        for key in ("robot1", "robot2"):
            if key in payload:
                name = str(payload[key]).strip()[:40]
                if name:
                    state[key] = name
        return jsonify(snapshot())

@app.post("/api/start")
def start_battle():
    with lock:
        state.update({
            "attacks1": 0, "attacks2": 0, "winner": "", "reason": "",
            "elapsed_seconds": 0, "started_at": time.time(),
            "status": "BATALLA EN CURSO", "phase": "running"
        })
        return jsonify(snapshot())

@app.post("/api/pause")
def pause_battle():
    with lock:
        if state["phase"] == "running" and state["started_at"] is not None:
            state["elapsed_seconds"] = int(time.time() - state["started_at"])
        state["started_at"] = None
        state["phase"] = "paused"
        state["status"] = "BATALLA PAUSADA"
        return jsonify(snapshot())

@app.post("/api/finish")
def finish_battle():
    payload = request.get_json(silent=True) or {}
    with lock:
        if state["phase"] == "running" and state["started_at"] is not None:
            state["elapsed_seconds"] = int(time.time() - state["started_at"])
        state["started_at"] = None
        state["phase"] = "finished"
        state["status"] = "BATALLA FINALIZADA"
        state["winner"] = str(payload.get("winner", "")).strip()[:40]
        state["reason"] = str(payload.get("reason", "")).strip()[:80]
        return jsonify(snapshot())

@app.post("/api/next")
def next_battle():
    payload = request.get_json(silent=True) or {}
    with lock:
        next_number = state["battle_number"] + 1
        pairs = [
            ("/R_Amarillo.png", "/R_Morado.png", "AMARILLO", "MORADO"),
            ("/R_Rojo.png", "/R_Verde.png", "ROJO", "VERDE")
        ]
        pair = pairs[(next_number - 1) % 2]
        state.update({
            "robot1": str(payload.get("robot1", pair[2])).strip()[:40] or pair[2],
            "robot2": str(payload.get("robot2", pair[3])).strip()[:40] or pair[3],
            "robot1_image": pair[0], "robot2_image": pair[1],
            "battle_number": next_number,
            "attacks1": 0, "attacks2": 0, "elapsed_seconds": 0,
            "started_at": None, "winner": "", "reason": "",
            "status": "PREPARADOS PARA LA BATALLA", "phase": "ready"
        })
        return jsonify(snapshot())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
