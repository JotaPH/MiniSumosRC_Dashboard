from flask import Flask, jsonify, request, render_template, send_from_directory
from threading import Lock, Thread
import time

app = Flask(__name__)
lock = Lock()

state = {
    "robot1": "AMARILLO", "robot2": "MORADO",
    "robot1_image": "/Imagenes/R_Amarillo.png", "robot2_image": "/Imagenes/R_Morado.png",
    "battle_number": 1,
    "attacks1": 0, "attacks2": 0,
    "status": "PREPARADOS PARA LA BATALLA",
    "elapsed_seconds": 0, "started_at": None,
    "winner": "", "reason": "", "phase": "ready",
    "ui_action": "", "ui_action_id": 0
}

def snapshot():
    data = dict(state)
    if data["phase"] == "running" and data["started_at"] is not None:
        data["elapsed_seconds"] = time.time() - data["started_at"]
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
    allowed = {"Imagenes/Fondo.jpg", "Imagenes/Fondo_Ganar.jpg", "Imagenes/Fondo_Proxima.jpg", "Imagenes/No_Batalla.png", "Imagenes/R_Amarillo.png", "Imagenes/R_Morado.png", "Imagenes/R_Rojo.png", "Imagenes/R_Verde.png", "Audios/videoplayback.m4a", "Audios/audio_final.m4a"}
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
            state["elapsed_seconds"] += time.time() - state["started_at"]
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
            ("/Imagenes/R_Amarillo.png", "/Imagenes/R_Morado.png", "AMARILLO", "MORADO"),
            ("/Imagenes/R_Rojo.png", "/Imagenes/R_Verde.png", "ROJO", "VERDE")
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

def terminal_command_loop():
    print("\nComandos: r.NOMBRE | rr.NOMBRE | t.MIN.SEG.CENTESIMAS | mot.MOTIVO | ini | pau | con | fin | g.1 | g.2 | p.NOMBRE1.NOMBRE2 | pn | home | salir")
    while True:
        try:
            raw = input("MiniSumos > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            continue
        command = raw.lower()
        if command in ("salir", "exit", "quit"):
            print("Consola de comandos cerrada; el dashboard sigue activo.")
            break
        try:
            with lock:
                if command.startswith("rr.") and raw[3:].strip():
                    state["robot2"] = raw[3:].strip()[:40]
                elif command.startswith("r.") and raw[2:].strip():
                    state["robot1"] = raw[2:].strip()[:40]
                elif command.startswith("t."):
                    parts = raw.split(".")
                    if len(parts) != 4 or not all(p.isdigit() for p in parts[1:]):
                        raise ValueError("Formato: t.MINUTOS.SEGUNDOS.CENTESIMAS (ej. t.1.23.45)")
                    minutes, seconds, centiseconds = map(int, parts[1:])
                    if seconds > 59 or centiseconds > 99:
                        raise ValueError("Segundos: 0-59; centésimas: 0-99.")
                    elapsed = minutes * 60 + seconds + centiseconds / 100
                    state["elapsed_seconds"] = elapsed
                    if state["phase"] == "running":
                        state["started_at"] = time.time() - elapsed
                elif command.startswith("mot.") and raw[4:].strip():
                    state["reason"] = raw[4:].strip().replace("_", " ")[:80]
                elif command == "home":
                    state.update({"ui_action": "home", "ui_action_id": state["ui_action_id"] + 1})
                elif command == "ini":
                    state.update({"attacks1": 0, "attacks2": 0, "winner": "",
                                  "started_at": time.time() - state["elapsed_seconds"],
                                  "status": "BATALLA EN CURSO", "phase": "running"})
                elif command == "pau":
                    if state["phase"] == "running" and state["started_at"] is not None:
                        state["elapsed_seconds"] += time.time() - state["started_at"]
                    state.update({"started_at": None, "status": "BATALLA PAUSADA", "phase": "paused"})
                elif command == "con":
                    state.update({"started_at": time.time() - state["elapsed_seconds"],
                                  "status": "BATALLA EN CURSO", "phase": "running"})
                elif command == "fin":
                    if state["phase"] == "running" and state["started_at"] is not None:
                        state["elapsed_seconds"] += time.time() - state["started_at"]
                    state.update({"started_at": None, "status": "BATALLA FINALIZADA", "phase": "finished"})
                elif command in ("g.1", "g.2"):
                    if state["phase"] == "running" and state["started_at"] is not None:
                        state["elapsed_seconds"] += time.time() - state["started_at"]
                    state.update({"started_at": None, "phase": "finished", "status": "BATALLA FINALIZADA",
                                  "winner": state["robot1"] if command == "g.1" else state["robot2"],
                                  "reason": state["reason"] or "DECISIÓN ARBITRAL", "ui_action": "winner",
                                  "ui_action_id": state["ui_action_id"] + 1})
                elif command.startswith("p."):
                    parts = raw.split(".")
                    if len(parts) < 3 or not parts[1].strip() or not ".".join(parts[2:]).strip():
                        raise ValueError("Formato: p.NOMBRE1.NOMBRE2")
                    state.update({"robot1": parts[1].strip()[:40],
                                  "robot2": ".".join(parts[2:]).strip()[:40],
                                  "ui_action": "next", "ui_action_id": state["ui_action_id"] + 1})
                elif command == "pn":
                    state.update({"ui_action": "no_battles", "ui_action_id": state["ui_action_id"] + 1})
                else:
                    raise ValueError("Comando no reconocido.")
            print("Comando aplicado:", raw)
        except ValueError as exc:
            print("Error:", exc)

if __name__ == "__main__":
    Thread(target=terminal_command_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
