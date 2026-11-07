# Suivi stock BoosterStop

Historique du stock des 8 machines BoosterStop en Suisse, avec un tableau de bord pour :

- voir chaque machine étage par étage, à n'importe quel moment de l'historique ;
- comparer deux moments précis (point A / point B), par exemple **juste avant et juste après un reload** ;
- compter, entre A et B, les unités vendues, le CA estimé, les unités rechargées et les changements de produit ;
- retrouver tous les reloads détectés, machine par machine.

Tableau de bord : https://laurenth91.github.io/boosterstop-tracker/

## Comment ça marche

- `collect.py` interroge l'API publique de la page stock (`boosterstop-stock.cold-water-7039.workers.dev/stock?machine=N`), toutes les 15 minutes via GitHub Actions (`.github/workflows/collect.yml`).
- Seuls les emplacements qui ont changé sont enregistrés, dans `data/snapshots/AAAA-MM.jsonl`. Chaque fichier mensuel commence par l'état complet des machines. Le dépôt grossit d'environ 0,5 Mo par mois.
- `index.html` est le tableau de bord. Il est servi par GitHub Pages et lit directement les fichiers de `data/`.

**Règles de calcul :**

- **Vente** : baisse de stock d'un emplacement entre deux instantanés. Le CA est estimé au prix affiché.
- **Reload** : un instantané où au moins un emplacement a été rechargé (hausse de stock).
- **Changement de produit** : un emplacement dont le produit change. Il compte comme un retrait suivi d'un chargement, pas comme des ventes.
- **Limite** : si des ventes et un reload ont lieu sur le même emplacement dans le même quart d'heure, seul le solde net est visible.

## Réglages GitHub nécessaires

1. **Settings → Actions → General → Workflow permissions** : **Read and write permissions**, pour que la collecte puisse enregistrer l'historique.
2. **Settings → Pages** : **Deploy from a branch**, branche `main`, dossier `/ (root)`.
3. Onglet **Actions** → « Instantané du stock » → **Run workflow** pour un instantané immédiat.

Pour ouvrir directement une machine, ajoutez `?m=rive` à l'adresse (ou `charmilles`, `petit-lancy`, `plainpalais`, `thonex`, `carouge`, `king-jouet-carouge`, `king-jouet-ecublens`).

## À savoir

- GitHub peut retarder les tâches planifiées de quelques minutes aux heures chargées.
- Si une nouvelle machine apparaît sur boosterstop.com, ajoutez-la dans `MACHINES`, dans `collect.py` et dans `index.html`. L'index du Worker se trouve dans le code source de `stock.html`.
- Pour tester en local :

  ```bash
  python collect.py
  ```

  puis

  ```bash
  python -m http.server
  ```

  et ouvrez http://localhost:8000.
