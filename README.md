# Velox-lab

Progetto ciclismo con backend FastAPI e frontend statico.

## Setup rapido

1. Crea e attiva un ambiente virtuale Python.
2. Installa dipendenze:

   pip install -r requirements.txt

3. Imposta credenziali admin locali tramite variabili d'ambiente:

   Per questa sessione cmd:
   set ADMIN_USERNAME=tuo_username
   set ADMIN_PASSWORD=tua_password_forte

   Oppure in modo permanente:
   setx ADMIN_USERNAME "tuo_username"
   setx ADMIN_PASSWORD "tua_password_forte"

   Se usi setx, chiudi e riapri il terminale.

4. Avvia il backend:

   uvicorn backend.main:app --reload

## Note sicurezza

- Le credenziali admin vengono lette solo da ADMIN_USERNAME e ADMIN_PASSWORD.
- Non pubblicare mai password reali in file versionati.
- `ciclismo.db` e file database locali non devono essere pubblicati.
