#!/usr/bin/env python3
"""Prend un instantané du stock de toutes les machines BoosterStop.

Un instantané n'est ajouté à l'historique que si le stock a changé depuis
le précédent, pour garder le dépôt léger. data/state.json est mis à jour à
chaque changement, et au moins toutes les HEARTBEAT_HOURS heures pour
montrer que la collecte tourne toujours.

Fichiers produits :
  data/snapshots/AAAA-MM.jsonl  une ligne JSON par instantané
  data/catalog.json             goods_id -> nom, image
  data/state.json               dernière vérification, liste des mois
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = os.environ.get("BOOSTERSTOP_API", "https://boosterstop-stock.cold-water-7039.workers.dev")
DATA = Path(os.environ.get("BOOSTERSTOP_DATA", Path(__file__).parent / "data"))
HEARTBEAT_HOURS = 6

# slug -> index attendu par le Worker (repris de boosterstop.com/stock.html)
MACHINES = {
    "rive": 0,
    "charmilles": 1,
    "petit-lancy": 2,
    "plainpalais": 5,
    "thonex": 7,
    "carouge": 4,
    "king-jouet-carouge": 3,
    "king-jouet-ecublens": 6,
}


def fetch(idx, tries=3):
    url = f"{API}/stock?machine={idx}"
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "boosterstop-tracker"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
            if data.get("ok"):
                return data
            raise ValueError("réponse ok=false")
        except Exception as e:  # noqa: BLE001
            if attempt == tries - 1:
                print(f"  ! machine {idx}: {e}", file=sys.stderr)
                return None
            time.sleep(2 * (attempt + 1))


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def replay(path):
    """Rejoue un fichier mensuel et renvoie l'état final {slug: {slot: [slot, gid, stock, vol, price]}}."""
    known = {}
    if not path.exists():
        return known
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("k"):  # état complet
            for slug, slots in rec["m"].items():
                known[slug] = {s[0]: s for s in slots}
        else:  # seulement les rails modifiés ; [n] seul = rail retiré
            for slug, slots in rec["m"].items():
                cur = known.setdefault(slug, {})
                for s in slots:
                    if len(s) == 1:
                        cur.pop(s[0], None)
                    else:
                        cur[s[0]] = s
    return known


def append(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")


def main():
    fake_now = os.environ.get("BOOSTERSTOP_NOW")  # pour les tests uniquement
    now = datetime.fromisoformat(fake_now) if fake_now else datetime.now(timezone.utc).replace(microsecond=0)
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    state = load_json(DATA / "state.json", {"months": []})
    catalog = load_json(DATA / "catalog.json", {})

    snap, errors, seen_ids = {}, [], set()
    for slug, idx in MACHINES.items():
        data = fetch(idx)
        if data is None:
            errors.append(slug)
            continue
        mid = data.get("machine_id")
        if mid in seen_ids:  # même garde-fou que le site : un index peut pointer vers une machine déjà vue
            errors.append(slug)
            continue
        seen_ids.add(mid)
        slots = []
        for s in data.get("slots", []):
            if not s.get("configured"):
                continue
            gid = s.get("goods_id")
            slots.append([int(s["slot_num"]), gid, int(s.get("stock") or 0),
                          int(s.get("volume") or 0), float(s.get("price") or 0)])
            if gid is not None:
                img = s.get("image") or ""
                catalog[str(gid)] = {
                    "name": (s.get("goods_name") or "").strip(),
                    "image": "" if img.rstrip("/") == "https://eu.zhongdacloud.com" else img,
                }
        slots.sort()
        snap[slug] = slots

    print(f"{ts}: {len(snap)} machines lues, erreurs: {errors or 'aucune'}")
    if not snap:
        sys.exit("Aucune machine lue, rien n'est enregistré.")

    month = now.strftime("%Y-%m")
    new_month = False
    f = DATA / "snapshots" / f"{month}.jsonl"
    if f.exists():
        previous = replay(f)
    else:
        # nouveau mois : le fichier commence par l'état complet, pour rester lisible seul
        prev_months = [m for m in state.get("months", []) if m < month]
        previous = replay(DATA / "snapshots" / f"{prev_months[-1]}.jsonl") if prev_months else {}
        full = {slug: sorted(slots.values()) for slug, slots in previous.items()}
        if full:
            append(f, {"t": ts, "k": 1, "m": full})
        new_month = True
        state.setdefault("months", []).append(month)
        state["months"] = sorted(set(state["months"]))

    delta = {}
    for slug, slots in snap.items():
        old = previous.get(slug, {})
        new = {s[0]: s for s in slots}
        d = [s for n, s in sorted(new.items()) if old.get(n) != s]
        d += [[n] for n in sorted(old) if n not in new]
        if d:
            delta[slug] = d

    if delta:
        rec = {"t": ts, "m": delta}
        if errors:
            rec["err"] = errors
        append(f, rec)
        state["last_change"] = ts
        print(f"  changement sur : {', '.join(f'{k} ({len(v)} rails)' for k, v in delta.items())}")
    else:
        print("  aucun changement")
    changed = bool(delta) or new_month

    last_check = state.get("last_check")
    stale = not last_check or (now - datetime.fromisoformat(last_check.replace("Z", "+00:00"))).total_seconds() >= HEARTBEAT_HOURS * 3600
    if changed or stale:
        state["last_check"] = ts
        state["errors"] = errors
        write_json(DATA / "state.json", state)
        write_json(DATA / "catalog.json", catalog)


if __name__ == "__main__":
    main()
