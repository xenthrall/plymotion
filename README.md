# Plymotion

Convierte cualquier video o GIF en la animación de arranque (Plymouth) de tu
Linux, desde una app de escritorio moderna. El foco es Ubuntu con GNOME.

## Características

- **Crear tema:** elige o arrastra un video o GIF, recórtalo sobre la línea de tiempo y ve en vivo cuántos frames salen y cuánto dura el loop
- **Simulador de arranque:** reproduce el tema como lo hará Plymouth, a 50 Hz y a tamaño real sobre una pantalla simulada, sin reiniciar
- **Galería:** tus temas, animados al pasar el cursor; se instalan con un clic
- **Sistema:** temas instalados; puedes activar, desinstalar, restaurar el backup, probar en vivo o volver a modo texto
- **Logo del login:** reemplaza el logo de GDM y previsualízalo sobre una réplica de la pantalla de login
- **Secuencias:** convierte imágenes en MP4 o GIF, por ejemplo para rehacer un tema
- **Seguro:** backup automático; cada acción de administrador pasa por un único prompt de `pkexec`, y un tema roto nunca impide arrancar

## Puesta en marcha

Plymotion no se instala en el sistema: se ejecuta desde este repo cuando
quieres personalizar el arranque, y al cerrar la ventana (o la terminal) no
queda nada corriendo. Todo lo que genera (galería de temas, preferencias,
videos de Secuencias) se guarda en `library/`, dentro del repo e ignorado
por git.

Solo toca el sistema lo que pides explícitamente, siempre tras un prompt de
`pkexec`: instalar o activar temas en `/usr/share/plymouth/themes` (con
backup en `/var/backups/plymotion`) y el logo del login en
`/usr/share/plymotion` y `/usr/share/gdm/dconf`.

Dependencias del sistema (Ubuntu/Debian):

```bash
sudo apt install ffmpeg python3-gi gir1.2-webkit2-4.1
```

- `ffmpeg`: extrae los frames y arma los videos.
- `python3-gi` y `gir1.2-webkit2-4.1`: la ventana nativa (WebKitGTK). Sin ellas, usa `--browser`.
- Para el entorno: [uv](https://docs.astral.sh/uv/) y Node 20 o superior (solo para compilar el cliente).

Primera vez:

```bash
git clone https://github.com/xenthrall/plymotion.git
cd plymotion
uv sync                           # crea .venv dentro del repo
npm --prefix frontend install     # node_modules dentro de frontend/
npm --prefix frontend run build   # compila el cliente en src/plymotion/web/
```

Cada vez que quieras usarlo:

```bash
uv run plymotion            # ventana nativa; ciérrala y listo
uv run plymotion --browser  # mismo servidor en el navegador; Ctrl+C para salir
```

## Arquitectura

```
ventana pywebview ─▶ cliente React ─(REST + SSE)─▶ API FastAPI ─▶ servicios + jobs ─▶ core
                                                                                     (ffmpeg, Pillow,
                                                                                      Plymouth, GDM, pkexec)
```

```
src/plymotion/
├── core/          # dominio: video_extractor, frame_processor, template_generator,
│                  # installer (pkexec), login_logo, library, image_sequence, sorting
├── services/      # casos de uso con progreso y cancelación (convert, themes, login_logo, sequence)
├── jobs/          # JobManager: hilos, eventos en vivo, cancelación, lock "system" para pkexec
├── api/           # FastAPI: app.py, security.py, schemas.py, routers/
├── desktop.py     # entry point `plymotion`: Uvicorn + ventana pywebview
└── web/           # build del cliente (generado con npm run build, no versionado)
frontend/          # cliente: React 19, Vite, TypeScript, Tailwind v4, Radix/shadcn, TanStack Query
tests/             # pytest: core, servicios, jobs y API
docs/              # investigación técnica de Plymouth y GDM
```

- **Tareas largas** (convertir, instalar, ffmpeg) corren como *jobs*. La API responde `202` y el progreso llega por un único stream SSE (`/api/events`).
- **Acciones con `pkexec`** comparten un lock: nunca hay dos prompts de contraseña ni dos `update-initramfs` a la vez (la API responde `409`).
- **Servidor local seguro:** escucha solo en `127.0.0.1`, en un puerto aleatorio y con un token nuevo en cada arranque, que viaja en una cookie HttpOnly/SameSite=Strict. Además valida `Host` y `Origin` y exige el header `X-Plymotion` en cada escritura.
- **Archivos:** el selector nativo (GTK) entrega rutas reales, así que no se suben videos. Arrastrar y soltar también funciona en la ventana nativa.

## Desarrollo

```bash
uv run plymotion --dev            # API en :8765 con /api/docs, imprime la URL de acceso
npm --prefix frontend run dev     # Vite en :5173 con recarga en caliente; abre la URL impresa
```

```bash
uv run pytest && uv run ruff check src tests && uv run pyright
npm --prefix frontend run lint && npm --prefix frontend run typecheck
npm --prefix frontend run gen:api  # tras cambiar la API: regenera openapi.json y los tipos TS
```

## Seguridad de Plymouth

Un tema roto o corrupto **nunca** impide arrancar: Plymouth cae al modo texto y
systemd sigue. Desde la app, **Sistema → Volver a modo texto** es el respaldo
garantizado. Si no puedes entrar al escritorio:

```bash
# En GRUB, pulsa 'e' y añade a la línea del kernel:
plymouth.enable=0

# O desde una TTY (Ctrl+Alt+F3):
sudo update-alternatives --set default.plymouth /usr/share/plymouth/themes/text/text.plymouth
sudo update-initramfs -u -k all
```

Detalles técnicos (initramfs, nombres de archivo, BGRT, GDM) en
[`docs/plymouth-ubuntu-gnome.md`](docs/plymouth-ubuntu-gnome.md).

## License

MIT
