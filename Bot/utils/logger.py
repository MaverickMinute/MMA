import json
import os

LOG_FILE = "data/logs.json"

def _load():
    if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
        with open(LOG_FILE, "w") as f:
            json.dump({"count": 0, "logs": {}, "notes": {}, "wipes": {}}, f)
    with open(LOG_FILE, "r") as f:
        data = json.load(f)
    if "notes" not in data:
        data["notes"] = {}
    if "wipes" not in data:
        data["wipes"] = {}
    return data

def _save(data):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_log_number():
    data = _load()
    data["count"] += 1
    _save(data)
    return data["count"]

def reset_log_count():
    data = _load()
    data["count"] = 0
    _save(data)

def save_log(log_number, message_id, user_id, action, type=None, reason=None):
    data = _load()
    data["logs"][str(log_number)] = {
        "message_id": message_id,
        "user_id": str(user_id),
        "action": action,
        "type": type,
        "reason": reason
    }
    _save(data)

def get_log(log_number):
    data = _load()
    return data["logs"].get(str(log_number))

def update_log(log_number, **kwargs):
    data = _load()
    if str(log_number) in data["logs"]:
        data["logs"][str(log_number)].update(kwargs)
        _save(data)
        return True
    return False

def get_user_history(user_id):
    data = _load()
    user_id = str(user_id)
    history = {
        "warns": [],
        "bans": [],
        "unbans": [],
        "kicks": [],
        "timeouts": [],
        "untimeouts": [],
        "undos": []
    }
    for log_num, entry in data["logs"].items():
        if entry.get("user_id") != user_id:
            continue
        action = entry.get("action", "")
        record = {**entry, "log_number": log_num}
        if action == "warn":
            history["warns"].append(record)
        elif action == "ban":
            history["bans"].append(record)
        elif action == "unban":
            history["unbans"].append(record)
        elif action == "kick":
            history["kicks"].append(record)
        elif action == "timeout":
            history["timeouts"].append(record)
        elif action == "untimeout":
            history["untimeouts"].append(record)
        elif action.startswith("undo_"):
            history["undos"].append(record)
    return history

def get_notes(user_id):
    data = _load()
    return data["notes"].get(str(user_id), [])

def add_note(user_id, note, moderator_id):
    data = _load()
    user_id = str(user_id)
    if user_id not in data["notes"]:
        data["notes"][user_id] = []
    data["notes"][user_id].append({
        "note": note,
        "moderator_id": str(moderator_id)
    })
    _save(data)

def wipe_user_record(user_id, moderator_id):
    data = _load()
    user_id = str(user_id)

    # Remove all logs for this user
    data["logs"] = {
        k: v for k, v in data["logs"].items()
        if v.get("user_id") != user_id
    }

    # Remove notes
    if user_id in data["notes"]:
        del data["notes"][user_id]

    # Track wipe
    if user_id not in data["wipes"]:
        data["wipes"][user_id] = []
    data["wipes"][user_id].append({
        "moderator_id": str(moderator_id),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    })

    _save(data)

def wipe_all_records(moderator_id):
    data = _load()

    # Collect all user IDs that had records
    wiped_users = set(v.get("user_id") for v in data["logs"].values() if v.get("user_id"))
    wiped_users.update(data["notes"].keys())

    # Clear logs and notes
    data["logs"] = {}
    data["notes"] = {}

    # Track wipes for every affected user
    for user_id in wiped_users:
        if user_id not in data["wipes"]:
            data["wipes"][user_id] = []
        data["wipes"][user_id].append({
            "moderator_id": str(moderator_id),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        })

    _save(data)

def get_wipes(user_id):
    data = _load()
    return data["wipes"].get(str(user_id), [])