# Despliegue de Mente Viva (Render + Google AI Studio)

Costo objetivo: **Render Starter 7 USD/mes + disco 1 GB 0.25 USD/mes ≈ 145 MXN/mes** + tokens de Gemini (tope duro 500 MXN configurado en la plataforma). Un solo servicio, sin staging, sin dominio propio.

## 1. API key de Gemini (10 minutos)

1. Entra a **https://aistudio.google.com** con la cuenta del área (condor.odoo@gmail.com) → *Get API key* → *Create API key* (crea un proyecto nuevo, p. ej. `mente-viva`).
2. Activa la **facturación** del proyecto (Google Cloud → Billing) para pasar al nivel de pago: así los datos de las conversaciones **no se usan para entrenar modelos** y no hay límites de cuota del nivel gratuito. Con 10 personas el gasto esperado es de 20–60 MXN/mes; el tope real lo pone Mente Viva.
3. Opcional: en Google Cloud → *Billing → Budgets & alerts* crea una alerta de 25 USD.
4. Copia la key; se captura en Render en el paso 3 (nunca en el código ni en el repo).

## 2. Repositorio en GitHub (5 minutos)

1. Crea un repositorio **privado** `MENTE-VIVA` en la cuenta del área.
2. Sube el contenido de esta carpeta (sin `.env`, sin `data/`): puedes arrastrar los archivos en la web de GitHub o con git:
   ```bash
   git init && git add . && git commit -m "Mente Viva v1.0.0" && git branch -M main
   git remote add origin https://github.com/<usuario>/MENTE-VIVA.git && git push -u origin main
   ```

## 3. Render (15 minutos)

1. Crea un **workspace nuevo** en https://render.com (plan Hobby, gratis) con la cuenta del área y conecta GitHub.
2. *New → Blueprint* → elige el repo `MENTE-VIVA`. Render lee `render.yaml`: servicio web **Starter**, disco de 1 GB en `/data`, `healthCheckPath=/salud`.
3. Antes de aplicar, captura las variables marcadas `sync: false`:
   - `GEMINI_API_KEY` = la key del paso 1
   - `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD` = cuenta del equipo Mente Viva (contraseña larga; se puede cambiar dentro)
   - `EMPRESA_INICIAL` = `Ingeniería Cóndor`
   - `RRHH_INICIAL_EMAIL` / `RRHH_INICIAL_PASSWORD` = primer usuario de RRHH (se le pedirá cambiar la contraseña al entrar)
4. *Apply*. El primer build tarda 2–4 minutos. La URL será `https://mente-viva.onrender.com` (o similar).
5. Verifica `https://<tu-url>/salud` → `{"ok": true, "version": "1.0.0"}`.

Si prefieres crearlo a mano (sin Blueprint): *New → Web Service* → runtime Python → Build `pip install -r requirements.txt` → Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` → plan Starter → *Disks*: `/data`, 1 GB → variables de `.env.example` con `APP_ENV=production`, `DATA_DIR=/data`, `SCHEDULE_ENABLED=1`.

## 4. Primer arranque (10 minutos)

1. Entra como **superadmin** (`/admin`): revisa modelo (`gemini-3.8-flash` / `gemini-3.5-flash-lite`), tope mensual (500 MXN), tipo de cambio y máximo de búsquedas web. Comprueba que la empresa inicial tenga habilitada la **Ruta Delivery Manager**.
2. Entra como **RRHH**: cambia la contraseña, crea las áreas, da de alta a los directores y colaboradores (`/gestion`). Cada alta genera una **contraseña temporal** que se comparte por un canal seguro; la persona la cambia en su primer acceso.
3. Cada colaborador: *Hoy → Empezar mi diagnóstico* (cuestionario + entrevista con Elena, ~25 min). Al terminar aparecen sus niveles y planes; los planes de habilidades fuera de su rol quedan en *Aprobaciones* para RRHH.
4. Directores: registran la **evaluación del líder** cada mes (`/equipo → Evaluar`) para activar los índices de aplicación y transferencia.

## 5. Operación

- **Presupuesto**: al 80 % todas las pantallas avisan; al 100 % los agentes se detienen y el superadmin amplía el tope en `/admin`. El contador se reinicia cada mes.
- **Uso**: `/admin/uso` muestra tokens y costo por origen y por día; `/admin/bitacora` los eventos (accesos, seguridad, IA, aprobaciones).
- **Respaldo**: el disco de Render guarda `/data/mente_viva.db` (SQLite en modo WAL). Render toma snapshots del disco; para un respaldo manual usa *Shell* del servicio: `cp /data/mente_viva.db /data/respaldo_$(date +%F).db` y descárgalo con `render disks`/SFTP, o exporta los tableros a Excel desde la plataforma.
- **Actualizaciones**: cada push a `main` redespliega (autoDeploy). El esquema de base se migra solo al arrancar.
- **Escalar**: si crece el uso, sube la instancia a Standard (25 USD) o el disco a 2 GB; ningún cambio de código.

## 6. Verificación rápida tras desplegar

1. `GET /salud` responde.
2. Entrar/salir con RRHH; alta de un colaborador de prueba.
3. Diagnóstico completo con Elena (real) → `/mi-diagnostico` con competencias y planes.
4. Una sesión con Celeste y una con Juan → reportes con score, KPIs y evidencia; lectura del Analista visible en la ficha para el director.
5. `/admin/uso` refleja el costo (≈ 0.05–0.15 MXN por turno, 1–2 MXN por sesión).
