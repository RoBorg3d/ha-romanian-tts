Iată versiunea curățată, cu un aspect strict tehnic și profesional, fără niciun emoji. Formatarea Markdown cu blocurile de cod (care vor genera butoanele de "Copy" pe GitHub) a fost păstrată intactă.

---

# Ghid de Instalare: Server AI Local pentru Romanian TTS (Docker)

Acest ghid te va ajuta să pornești serverul care generează vocile (creierul asistentului tău) folosind Docker. Serverul va rula local pe calculatorul tău, păstrând totul 100% privat.

## Cerințe de Sistem (Foarte Important!)

Deoarece generarea de voce prin Inteligență Artificială (modelul XTTS-v2) este un proces complex, ai nevoie de o placă video dedicată pentru ca asistentul să îți răspundă rapid (în 1-2 secunde). Dacă rulezi pe procesor (CPU), o propoziție poate dura zeci de secunde.

* **Placă Video (GPU):** Doar **NVIDIA** (modelele AMD/Intel nu sunt suportate nativ de acest container pentru accelerare).
* **Memorie Video (VRAM):** Minim **6 GB VRAM** (8 GB sau mai mult este recomandat pentru stabilitate maximă).
* **Drivere:** Driverele NVIDIA trebuie să fie actualizate la zi pe calculatorul tău.

---

## Pasul 1: Instalarea Docker Desktop

Docker este programul care ne permite să rulăm serverul AI într-o "cutie" izolată (container), fără să instalăm zeci de programe complexe direct în sistemul de operare.

1. Descarcă **Docker Desktop** de pe site-ul oficial: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2. Instalează programul lăsând setările implicite (asigură-te că opțiunea **WSL 2** este bifată în timpul instalării, dacă ești pe Windows).
3. După instalare, deschide Docker Desktop și lasă-l să ruleze în fundal (vei vedea iconița cu balena în bara de jos).

---

## Pasul 2: Pregătirea Fișierelor și a Vocilor

1. Descarcă acest proiect de pe GitHub (folosind butonul verde **Code -> Download ZIP**) și extrage-l pe calculatorul tău (ex: `C:\Romanian-TTS`).
2. Intră în folderul `docker_server` (unde se află fișierele `Dockerfile` și `main.py`).
3. Creează un folder nou numit exact `voices` în interiorul acestuia.
4. Pune în acel folder fișierele tale audio de referință (`.wav`).
* *Sfat:* Fișierele trebuie să aibă 5-8 secunde, să fie extrem de clare și să nu aibă **absolut deloc** zgomot de fundal! (ex: `inna.wav`, `casandra.wav`).



---

## Pasul 3: Construirea Containerului (Build)

Acum vom crea containerul care conține modelul AI.

Deschide un terminal (Command Prompt sau PowerShell pe Windows, Terminal pe Mac/Linux), navighează în folderul proiectului și rulează comanda de mai jos.

> **Notă:** Acest proces va dura câteva minute, deoarece va descărca mediul Linux și bibliotecile AI necesare.

```bash
docker build -t romanian-tts-server .

```

*(Nu uita punctul `.` de la final, este esențial!)*

---

## Pasul 4: Pornirea Serverului

Odată ce construcția s-a terminat cu succes, e timpul să pornim motorul!

Rulează comanda potrivită pentru sistemul tău de operare. Această comandă îi spune Docker-ului să folosească placa ta video (`--gpus all`) și să lege folderul tău local `voices` direct în interiorul serverului.

**Pentru Windows (Command Prompt - CMD):**

```cmd
docker run -d --name ro_tts_server --gpus all -p 8020:8020 -v "%cd%\voices:/app/voices" romanian-tts-server

```

**Pentru Windows (PowerShell):**

```powershell
docker run -d --name ro_tts_server --gpus all -p 8020:8020 -v "${PWD}\voices:/app/voices" romanian-tts-server

```

**Pentru Linux / Mac / WSL:**

```bash
docker run -d --name ro_tts_server --gpus all -p 8020:8020 -v "$(pwd)/voices:/app/voices" romanian-tts-server

```

---

## Pasul 5: Testarea Serverului

Serverul tău rulează acum în fundal! La prima generare de voce va descărca modelul AI (aprox. 1.8 GB), deci prima interogare va dura un pic mai mult.

Ca să verifici dacă funcționează și dacă a găsit corect vocile tale, deschide un browser de internet și accesează:

```text
http://localhost:8020/voices/

```

Dacă pe ecran îți apare un text de tipul `[{"voice_id": "inna.wav", "name": "Inna"}]`, felicitări! Serverul tău local de Inteligență Artificială este funcțional și pregătit să comunice cu Home Assistant!

---

