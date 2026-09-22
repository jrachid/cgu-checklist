# cgu-checklist

Personne ne lit les conditions générales d'utilisation avant de cliquer sur « J'accepte ». `cgu-checklist` les lit à votre place et en tire une check-list des points qui comptent, chacun justifié par la clause exacte du texte.

```
127 paragraphes analysés — 20720 tokens (jev-1.13.0)

➖  Utilise vos données à des fins commerciales ou publicitaires   [not_mentioned=0.99 no=0.00 yes=0.01]
⚠️   Partage vos données avec des tiers   [not_mentioned=0.59 no=0.01 yes=0.40]
✅  Peut modifier les conditions sans votre accord explicite   [not_mentioned=0.00 no=0.03 yes=0.97]
      ↳ P105 (1.00) « Article 14 – Modifications des présentes CGU — DEEZER se réserve le droit de modifier à sa discrétion les présentes CGU… »
✅  Limite ou exclut sa responsabilité   [not_mentioned=0.00 no=0.00 yes=1.00]
      ↳ P046 (0.86) « ii) Il est expressément convenu que la responsabilité de DEEZER ne saurait être recherchée à quelque titre que ce soit… »
❌  Impose l'arbitrage ou un tribunal éloigné   [not_mentioned=0.00 no=1.00 yes=0.00]
      ↳ P126 (0.84) « En cas de litige, les parties chercheront une solution amiable avant toute action judiciaire… »
```

## Comment ça marche

L'analyse repose sur [Jev](https://docs.typesafe.ai), le modèle de TypeSafe. Jev ne rédige pas de texte : il répond à des questions typées avec des probabilités, ce qui permet au code de décider seul de ce qu'il affiche.

1. Le texte est extrait de la page (avec [trafilatura](https://trafilatura.readthedocs.io)), puis découpé en paragraphes numérotés `P000`, `P001`… Chaque titre d'article est rattaché au paragraphe qui le suit.
2. Chaque point de la check-list donne lieu à deux questions : la réponse (oui, non explicitement, non mentionné) et le paragraphe qui la justifie.
3. Les 16 questions partent dans **une seule requête** : Jev les évalue en parallèle, en 3 secondes environ, pour à peu près 0,001 $ par document.

| Symbole | Signification |
| --- | --- |
| ✅ | le texte autorise ce point (probabilité ≥ 0,7) |
| ❌ | le texte l'exclut explicitement |
| ➖ | le texte n'en parle pas |
| ⚠️ | Jev hésite : à vérifier soi-même |

« Non mentionné » est distinct de « non » : des CGU muettes sur un sujet ne l'interdisent pas pour autant.

## Installation

Il faut [uv](https://docs.astral.sh/uv/) et une clé d'API TypeSafe dans la variable d'environnement `TYPESAFE_API_KEY`.

```bash
git clone git@github.com:jrachid/cgu-checklist.git
cd cgu-checklist
export TYPESAFE_API_KEY=...
uv run cgu-checklist https://www.deezer.com/legal/cgu
```

Un fichier texte local fonctionne aussi, ce qui est utile pour les sites qui bloquent les téléchargements automatiques :

```bash
uv run cgu-checklist cgu.txt
```

## Limites connues

- **Les données personnelles sont souvent ailleurs.** Beaucoup de services décrivent l'usage des données dans une politique de confidentialité séparée, que l'outil ne lit pas encore : ces points ressortent alors « non mentionné ».
- **Le français est une langue secondaire pour Jev**, entraîné surtout en anglais. Les questions sont posées en anglais sur un texte français ; les résultats sont à valider sur davantage de documents.
- **Les documents très longs** (au-delà de 30 000 tokens environ) sont refusés plutôt que découpés.
- Plusieurs sites (BlaBlaCar, Vinted, Doctolib) refusent les téléchargements automatiques.

## L'extension Chrome

L'extension, construite avec [WXT](https://wxt.dev), repère un lien vers des CGU placé dans une phrase d'acceptation (« J'accepte les conditions… », « En vous inscrivant, vous acceptez… ») et affiche la check-list juste en dessous. Un clic sur un point déplie la clause citée ; « Voir la clause » ouvre les CGU directement surlignées sur ce passage.

La page des CGU est téléchargée par le navigateur, ce qui évite les blocages rencontrés depuis un serveur. Son HTML est envoyé au serveur d'analyse local, qui seul détient la clé d'API.

```bash
# 1. le serveur d'analyse, sur http://127.0.0.1:8787
uv run cgu-checklist-server

# 2. l'extension, dans un Chrome de développement qui la recharge à chaque modification
cd extension
npm install
npm run dev
```

Pour l'installer dans son propre Chrome : `npm run build`, puis `chrome://extensions` → « Mode développeur » → « Charger l'extension non empaquetée » → dossier `extension/.output/chrome-mv3`.

Le dossier `extension/fixtures` contient des pages d'inscription de test : `python3 -m http.server 8788 -d extension/fixtures`, puis ouvrir `http://127.0.0.1:8788/signup.html`.

## Licence

[MIT](LICENSE)
