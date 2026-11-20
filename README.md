# ☕ Infos du jour

Chaque matin, l'app parcourt les flux RSS de plusieurs journaux et sites, garde les articles des **dernières 24h**, les regroupe par sujet, rédige un **résumé** de chaque sujet (avec les **liens** vers les articles d'origine) et t'envoie une **notification à 8h00** (heure de Paris).

Rubriques :

| Rubrique | Sources |
|---|---|
| 🇫🇷 Politique française | Le Monde, franceinfo, Le Figaro, Libération, 20 Minutes, Google News |
| 🎮 Gaming mondial | Jeuxvideo.com, Gamekult, Millenium, IGN, Eurogamer, The Verge, Polygon |
| ⛏️ Minecraft & Valorant | Minecraft.net, Google News (FR + EN) |
| 📈 Big Tech, IA & Bourse | Les Echos, Numerama, The Verge, TechCrunch, CNBC, Google News + cours de Nvidia, Microsoft, Alphabet, Apple, Meta, Amazon, Tesla, AMD, Ubisoft, Nasdaq, S&P 500, CAC 40 |

Tout se règle dans [`news/sources.py`](news/sources.py) : ajouter un journal, une action, une rubrique.

## Comment ça marche

```
GitHub Actions (tous les jours ~5h30)
  → récupère les flux RSS + cours de bourse (Yahoo Finance)
  → regroupe et résume (Claude si clé API, sinon chapô des journaux)
  → publie la page sur GitHub Pages
  → programme une notification ntfy pour 8h00 → ton téléphone
```

Pas de serveur à payer : tout tourne sur GitHub. La « app » sur le téléphone, c'est :
- l'app **ntfy** (gratuite, Android/iOS) qui reçoit la notification ;
- la **page web** qui s'ouvre quand tu touches la notification. Tu peux l'ajouter à ton écran d'accueil (« Ajouter à l'écran d'accueil ») pour qu'elle se comporte comme une app.

## Installation (≈ 10 minutes)

1. **Activer GitHub Pages** : *Settings → Pages → Source : GitHub Actions*.
   ⚠️ Sur un dépôt **privé**, Pages nécessite un compte GitHub payant. Sinon, rends le dépôt public (il ne contient aucun secret).
2. **Choisir un topic ntfy** : un nom long et difficile à deviner, par ex. `infos-du-jour-k8f3q9x2`. (Sur ntfy.sh, quiconque connaît le nom peut lire/écrire dessus.)
3. **Sur ton téléphone** : installe *ntfy*, puis « + » → s'abonner à ce topic.
4. **Secrets du dépôt** (*Settings → Secrets and variables → Actions*) :
   - `NTFY_TOPIC` : le topic choisi (obligatoire pour la notification) ;
   - `ANTHROPIC_API_KEY` : clé API Claude (facultatif mais recommandé, voir plus bas).
5. **Tester** : onglet *Actions → Infos du jour → Run workflow* (notification immédiate cochée).

## Résumés : avec ou sans IA

- **Sans clé** : les articles similaires sont regroupés par mots communs dans le titre, et le résumé est le chapô fourni par le journal. Gratuit, mais le regroupement est approximatif (deux titres formulés différemment sur le même sujet restent séparés) et les flux Google News n'ont souvent pas de chapô.
- **Avec `ANTHROPIC_API_KEY`** : Claude regroupe les articles par événement, trie par importance, ignore les bons plans/pubs, et écrit un vrai résumé de 2-4 phrases en français. Modèle par défaut : `claude-opus-5-5` (effort `low`). Ordre de grandeur : quelques dizaines de centimes par jour. Pour réduire fortement le coût, crée une *variable* de dépôt `CLAUDE_MODEL` = `claude-haiku-5-5`.

Les résumés sont faits à partir des titres et chapôs des flux RSS (pas du texte intégral des articles, souvent payant) : vérifie les détails importants via les liens.

## Lancer en local

```bash
pip install -r requirements.txt
python -m news.main --demo --no-notify      # données fictives, sans réseau
python -m news.main --no-notify             # vraies données → site/index.html
NTFY_TOPIC=mon-topic python -m news.main --notify-now
python -m pytest -q                         # tests
```

## Limites à connaître

- **Horaire** : la page est générée vers 5h30-6h30 ; la notification est programmée côté ntfy pour arriver à 8h00 pile. La fenêtre « 24h » se termine donc à l'heure de génération, pas à 8h.
- GitHub **désactive les workflows planifiés** d'un dépôt public sans activité pendant 60 jours : il faut alors le réactiver dans l'onglet Actions.
- Les cours viennent d'une API Yahoo **non officielle** (peut changer sans prévenir, cours différés).
- Un flux RSS peut changer d'adresse ou disparaître : l'erreur est journalisée et la rubrique continue avec les autres sources.
