# Faveod — How to run (Python venv)

> `api` n'est **pas** une commande. Il faut lancer le module via l'interpréteur
> Python du venv : `python -m api`.

## 1. Activer le venv (Windows PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
# l'invite devient (.venv) PS ...
```

Si PowerShell bloque l'activation (politique d'exécution) :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Ou, sans activer le venv, utiliser directement le Python du venv :

```powershell
.\.venv\Scripts\python.exe -m api
```

## 2. Lancer l'API (FastAPI)

| Commande | Effet |
|----------|-------|
| `python -m api` | http://localhost:8000 (Swagger : `/docs`) |
| `python -m api --port 9000` | http://localhost:9000 |
| `python -m api --host 0.0.0.0` | accessible depuis le réseau (LAN/Docker) |
| `python -m api --port 9000 --host 0.0.0.0` | les deux |
| `python -m api --reload` | redémarre auto au changement de code (dev) |

Exemple exact pour votre cas :

```powershell
python -m api --port 9000 --host 0.0.0.0
```

Points de contrôle :
- UI Swagger : `http://localhost:9000/docs`
- ReDoc : `http://localhost:9000/redoc`
- Santé : `http://localhost:9000/api/health` → `{"status": "ok"}`

## 3. Lancer le frontend (React, autre terminal)

```powershell
cd frontend
npm install   # première fois seulement
npm run dev   # http://localhost:5173 (proxies /api vers le backend)
```

> Le proxy Vite vise `http://localhost:8000` par défaut. Si vous lancez le
> backend sur un autre port (ex. 9000), éditez `frontend/vite.config.ts` ou
> définissez `VITE_API_BASE=http://localhost:9000` avant de lancer `npm run dev`.

## 4. Installer le venv (si absent)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 5. Lancer les agents seuls (sans l'API)

```powershell
python -m control.tender_scout            # appels d'offres
python -m control.partner_scout           # partenaires
python -m control.event_scout             # événements + leads
python -m notifications.check             # vérif notifications
python -m chat.chat --question "Votre question ?"
```
