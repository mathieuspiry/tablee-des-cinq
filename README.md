# La Tablée des Cinq

Site des menus de la famille, servi par GitHub Pages sur https://menu.elmaax.fr

- `index.html` : la page (menu, liste de courses à cocher, recettes).
- `recipes.js` : la banque de recettes, dosées pour 5, avec calories calculées.
- `week.js` : le menu de la semaine en cours.
- `history.json` : les semaines passées (évite les répétitions).
- `generate_week.py` : compose le menu de la semaine suivante.
- `.github/workflows/menu.yml` : le robot qui lance la composition chaque vendredi matin et publie.

Pour forcer un nouveau menu à la main : onglet Actions du dépôt, « Menu de la semaine », « Run workflow ».
