#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compose le menu de la semaine prochaine pour La Tablée des Cinq.

Tourne chaque vendredi matin (GitHub Actions) et réécrit week.js + history.json.
Règles : 8 plats (dîners lundi à jeudi, samedi midi et soir, dimanche midi et soir),
vendredi soir libre ; équilibre 2 viande / 2 poisson / 3 végétarien / 1 plaisir ;
au moins 2 favoris ; aucune recette servie dans les 3 dernières semaines ;
légumes de saison ; le dimanche midi accueille le plat le plus long.

Usage : python3 generate_week.py [AAAA-MM-JJ du lundi visé] [--force]
Sans argument : le lundi qui suit la date du jour. Sans --force, le script
ne fait rien si la semaine visée est déjà dans l'historique.
"""
import json, random, re, sys, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECIPES_JS = ROOT / "recipes.js"
WEEK_JS = ROOT / "week.js"
HISTORY = ROOT / "history.json"

# Mois (1 à 12) où un ingrédient frais est de saison en France.
SEASON = {
    "Courgettes": range(5, 11), "Aubergine": range(6, 11), "Tomates": range(6, 11),
    "Tomates cerises": range(5, 11), "Poivron rouge": range(6, 11), "Concombre": range(5, 10),
    "Haricots verts": range(6, 10), "Basilic frais": range(5, 10),
    "Brocoli": [9, 10, 11, 12, 1, 2, 3, 4], "Patates douces": [9, 10, 11, 12, 1, 2, 3],
    "Épinards frais": [3, 4, 5, 6, 9, 10, 11], "Champignons de Paris": range(1, 13),
    "Salade verte": range(1, 13), "Carottes": range(1, 13), "Avocats": range(1, 13),
}
MONTH_NAMES = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
               "septembre", "octobre", "novembre", "décembre"]
SEASON_LINE = {
    1: "Plein hiver : soupes, gratins et plats mijotés réconfortants.",
    2: "Encore l'hiver : on mise sur les légumes racines, le brocoli et les épinards.",
    3: "Le printemps pointe : premiers épinards frais, encore des carottes et des patates douces.",
    4: "Printemps : les assiettes s'allègent, les salades reviennent.",
    5: "Mai : premières courgettes et tomates cerises, le retour des repas frais.",
    6: "Début d'été : tomates, courgettes et haricots verts à volonté.",
    7: "Plein été : cuisine rapide, salades composées et plats au four le soir.",
    8: "Août : ratatouille, tomates mozzarella et poissons grillés.",
    9: "Rentrée : les dernières tomates et courgettes, et le retour des brocolis.",
    10: "Automne : patates douces, brocolis et plats qui réchauffent.",
    11: "Novembre : veloutés, gratins et purées maison.",
    12: "Décembre : plats simples et chauds, un dimanche généreux.",
}
SLOTS = [("lun-diner", "Lundi", "Dîner"), ("mar-diner", "Mardi", "Dîner"), ("mer-diner", "Mercredi", "Dîner"),
         ("jeu-diner", "Jeudi", "Dîner"), ("ven-diner", "Vendredi", "Dîner"), ("sam-dej", "Samedi", "Déjeuner"),
         ("sam-diner", "Samedi", "Dîner"), ("dim-dej", "Dimanche", "Déjeuner"), ("dim-diner", "Dimanche", "Dîner")]
TARGET = {"viande": 2, "poisson": 2, "vege": 3, "plaisir": 1}


def load_recipes():
    src = RECIPES_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.RECIPES\s*=\s*(\[.*?\]);\s*\nwindow\.RAYONS", src, re.S)
    return json.loads(m.group(1))


def in_season(recipe, month):
    for i in recipe["ing"]:
        months = SEASON.get(i["n"])
        if months is not None and month not in months:
            return False
    return True


def next_monday(today):
    return today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)


def fr_date(d, with_month=True):
    return f"{d.day} {MONTH_NAMES[d.month - 1]}" if with_month else str(d.day)


def compose(recipes, history, monday, seed):
    rng = random.Random(seed)
    recent = {rid for w in history[-3:] for rid in w["recipes"]}
    month = monday.month
    pool = [r for r in recipes if r["id"] not in recent]
    by_cat = {}
    for cat, n in TARGET.items():
        seasonal = [r for r in pool if r["cat"] == cat and in_season(r, month)]
        off = [r for r in pool if r["cat"] == cat and not in_season(r, month)]
        # de saison d'abord ; on ne complète hors saison que si nécessaire
        by_cat[cat] = seasonal if len(seasonal) >= n + 1 else seasonal + off

    for attempt in range(300):
        chosen = []
        ok = True
        for cat, n in TARGET.items():
            cands = by_cat[cat][:]
            if len(cands) < n:
                ok = False
                break
            rng.shuffle(cands)
            # on favorise les favoris sans les imposer tous
            cands.sort(key=lambda r: (0 if r["fav"] and rng.random() < 0.6 else 1))
            chosen += cands[:n]
        if not ok:
            break
        mains = [r["ing"][0]["n"] for r in chosen]
        if len(set(mains)) < len(mains):      # deux fois le même produit principal
            continue
        if sum(1 for r in chosen if r["fav"]) >= 2:
            return place(chosen, rng)
    # secours : on relâche la contrainte de fraîcheur (3 semaines)
    rng2 = random.Random(seed + 1)
    chosen = []
    for cat, n in TARGET.items():
        cands = [r for r in recipes if r["cat"] == cat]
        rng2.shuffle(cands)
        chosen += cands[:n]
    return place(chosen, rng2)


def place(chosen, rng):
    """Répartit les 8 plats : le plus long au dimanche midi, le plaisir le samedi soir,
    les autres mélangés en évitant deux fois la même famille d'affilée."""
    chosen = chosen[:]
    sunday = max(chosen, key=lambda r: (r.get("weekend", False), r["total"]))
    chosen.remove(sunday)
    treat = next(r for r in chosen if r["cat"] == "plaisir")
    chosen.remove(treat)
    for _ in range(80):
        rng.shuffle(chosen)
        cats = [r["cat"] for r in chosen]
        if all(cats[i] != cats[i + 1] for i in range(len(cats) - 1)) and cats[5] != sunday["cat"]:
            break
    order = chosen[:4] + [None] + [chosen[4], treat, sunday, chosen[5]]
    return order


def intro(order, monday):
    favs = [r["name"].split(",")[0] for r in order if r and r["fav"]][:2]
    line = SEASON_LINE[monday.month]
    if favs:
        line += f" Au menu, deux favoris de la maison : {favs[0].lower()} et {favs[1].lower()}." if len(favs) == 2 \
            else f" Au menu, un favori de la maison : {favs[0].lower()}."
    sunday = order[7]
    if sunday and sunday["total"] >= 40:
        line += f" Dimanche midi, {sunday['name'].split(',')[0].lower()} : le four fait le travail."
    return line


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    today = dt.date.today()
    monday = dt.date.fromisoformat(args[0]) if args else next_monday(today)
    sunday = monday + dt.timedelta(days=6)
    iso = monday.isocalendar()
    week_id = f"{iso[0]}-W{iso[1]:02d}"

    history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
    if any(w["id"] == week_id for w in history) and not force:
        print(f"{week_id} déjà générée, rien à faire.")
        return

    recipes = load_recipes()
    order = compose(recipes, [w for w in history if w["id"] != week_id], monday, seed=int(monday.strftime("%Y%m%d")))
    if monday.month == sunday.month:
        label = f"Semaine du {monday.day} au {fr_date(sunday)} {sunday.year}"
    else:
        label = f"Semaine du {fr_date(monday)} au {fr_date(sunday)} {sunday.year}"

    week = {
        "id": week_id, "label": label, "start": monday.isoformat(), "generatedAt": today.isoformat(),
        "intro": intro(order, monday),
        "slots": [{"key": k, "day": d, "meal": m, "recipe": (order[i]["id"] if order[i] else None)}
                  for i, (k, d, m) in enumerate(SLOTS)],
    }
    WEEK_JS.write_text("// Menu de la semaine. Fichier régénéré automatiquement chaque vendredi matin par generate_week.py.\n"
                       "window.WEEK = " + json.dumps(week, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    history = [w for w in history if w["id"] != week_id]
    history.append({"id": week_id, "start": monday.isoformat(), "recipes": [r["id"] for r in order if r]})
    HISTORY.write_text(json.dumps(history[-52:], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(label)
    for i, (k, d, m) in enumerate(SLOTS):
        r = order[i]
        print(f"  {d:9s} {m:9s} {r['name'] if r else 'repas libre'}" + (f"  [{r['cat']}, {r['kcal']} kcal]" if r else ""))


if __name__ == "__main__":
    main()
