# Suivi stock BoosterStop

Historique du stock des 8 machines BoosterStop en Suisse, avec un tableau de bord pour :

- voir chaque machine étage par étage, à n'importe quel moment de l'historique ;
- comparer deux moments précis (point A / point B), en particulier **juste avant et juste après un reload donné** ;
- compter, entre A et B, les unités vendues, le CA estimé, les unités rechargées, les changements de produit et les **displays ouverts** pour remplir les rangées de boosters ;
- retrouver tous les reloads détectés, machine par machine.

Tableau de bord : https://laurenth91.github.io/boosterstop-tracker/

## Comment ça marche

- `collect.py` interroge l'API publique de la page stock (`boosterstop-stock.cold-water-7039.workers.dev/stock?machine=N`), toutes les 15 minutes via GitHub Actions (`.github/workflows/collect.yml`).
- Seuls les emplacements qui ont changé sont enregistrés, dans `data/snapshots/AAAA-MM.jsonl`. Chaque fichier mensuel commence par l'état complet des machines.
- `index.html` est le tableau de bord. Il est servi par GitHub Pages et lit directement les fichiers de `data/`.

**Règles de calcul :**

- **Vente** : baisse de stock d'un emplacement entre deux instantanés. Le CA est estimé au prix affiché.
- **Reload** : des rechargements (hausses de stock) espacés de moins d'une heure forment un seul reload, même s'il s'étale sur plusieurs instantanés.
- **Display ouvert** : pendant un reload, un display (ou une boîte) dont le stock baisse alors que le booster qu'il contient est rechargé dans le même quart d'heure est compté comme ouvert pour le réassort, et non comme vendu.
- **Bilan par produit** : on estime les boosters issus des displays (displays ouverts × boosters par display) et on les compare aux boosters rechargés.
  - Écart positif : apport extérieur.
  - Écart négatif : boosters gardés en réserve ou mis dans une autre machine.
- **Changement de produit** : un emplacement dont le produit change. Il compte comme un retrait suivi d'un chargement.
- **Limites** :
  - Si des ventes et un reload ont lieu sur le même emplacement dans le même quart d'heure, seul le solde net est visible.
  - Un display acheté par un client pendant un reload est compté comme ouvert.

## Displays

Le tableau de bord reconnaît les displays et les boîtes, par leur nom ou par un prix d'au moins CHF 60. Il relie chacun au booster de la même langue et de la même extension. Le nombre de boosters par display a une valeur par défaut :

- 36 pour Pokémon FR/EN ;
- 30 pour Pokémon JP/CN ;
- 24 pour One Piece, Dragon Ball, Lorcana et Yu-Gi-Oh! ;
- 9 pour une ETB.

Ces valeurs sont à vérifier. Elles se corrigent dans **Réglages des displays**, en bas de la vue d'une machine. Les réglages sont enregistrés dans le navigateur. Pour les rendre définitifs pour tout le monde, utilisez le bouton « Copier les réglages » et collez le résultat dans `config.json`.

## Réglages GitHub

- **Settings → Pages** : branche `main`, dossier `/ (root)`. C'est déjà configuré.
- Onglet **Actions** → « Instantané du stock » → **Run workflow** pour un instantané immédiat.

Pour ouvrir directement une machine, ajoutez `?m=rive` à l'adresse (ou `charmilles`, `petit-lancy`, `plainpalais`, `thonex`, `carouge`, `king-jouet-carouge`, `king-jouet-ecublens`).

## À savoir

- GitHub peut retarder les tâches planifiées de quelques minutes aux heures chargées.
- Si une nouvelle machine apparaît sur boosterstop.com, ajoutez-la dans `MACHINES`, dans `collect.py` et dans `index.html`.
