# Option 1 - Streamlit Interface

## Objectif

Ajouter une interface utilisateur simple sans changer l'architecture existante.

Le principe est:

- `gateway` reste le point d'entree unique
- Streamlit consomme uniquement les endpoints du gateway
- aucune modification n'est necessaire sur la stack principale

## Pourquoi cette option

Cette option est la plus simple si on veut:

- rendre la demo plus visuelle
- donner un point d'entree metier a un utilisateur non technique
- conserver Docker Compose comme mode d'execution principal

## Ce que l'on ajoute

- un service `streamlit-ui`
- une application Streamlit de demonstration
- un fichier `docker-compose.streamlit.yml` a utiliser en surcharge

## Fonctionnalites de la maquette

- connexion via le gateway
- affichage de l'etat des services
- prediction texte
- prediction image
- prediction multimodale

## Lancement

Depuis la racine du projet:

```powershell
docker compose -f docker-compose.yml -f options/option_1_streamlit_interface/docker-compose.streamlit.yml up -d --build
```

Puis ouvrir:

- Streamlit: `http://localhost:8501`
- Gateway Swagger: `http://localhost:8000/docs`

## Architecture cible

```text
[ User ]
   |
   v
[ Streamlit UI ]
   |
   v
[ Gateway ]
  / | \
 v  v  v
Text Image Training
```

## Limites

- Streamlit n'apporte pas de scalabilite par lui-meme
- cette option reste adaptee a une demo ou un petit usage interne
- le gateway actuel utilise une session memoire simple, donc ce n'est pas une solution multi-utilisateur de production
