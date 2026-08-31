# Plymotion

Convierte cualquier video en una animación de arranque personalizada para tu sistema Linux usando Plymouth.

## Características

- **GUI con tkinter**: Interfaz gráfica para seleccionar videos desde el gestor de archivos
- **CLI en Python**: Herramienta de línea de comandos para automatización
- **Frame-by-frame**: Extrae frames del video y los convierte en una secuencia de animación
- **Loop infinito**: La animación se repite continuamente durante el boot
- **Optimización automática**: Redimensiona y comprime frames para carga rápida
- **Instalación segura**: Backup automático del theme anterior antes de sobreescribir

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/xenthrall/plymotion.git
cd plymotion

# Instalar con uv
uv sync
```

## Uso

### Interfaz gráfica

```bash
plymotion gui
```

Se abre una ventana donde puedes:
1. Seleccionar un archivo de video con el botón "Examinar"
2. Configurar resolución, FPS y nombre del theme
3. Click "Convertir" - se extraen y optimizan los frames
4. Click "Instalar" - se instala el theme con backup automático
5. Reiniciar para ver el nuevo boot splash

### Línea de comandos

```bash
# Convertir video a theme (deja los archivos listos en ./plymotion-output)
plymotion convert --video-input mi_video.mp4

# Con opciones personalizadas
plymotion convert \
  --video-input mi_video.mp4 \
  --output-dir ./output \
  --resolution 1920x1080 \
  --fps 24 \
  --theme-name mi-theme

# Convertir E instalar de una vez (pide sudo)
plymotion convert --video-input mi_video.mp4 --install
```

### Opciones CLI

| Opción | Descripción | Default |
|--------|-------------|---------|
| `--video-input, -i` | Video de entrada (requerido) | - |
| `--output-dir, -o` | Directorio de salida | `./plymotion-output` |
| `--resolution, -r` | Resolución destino (WxH) | `1920x1080` |
| `--fps, -f` | Frames por segundo | `30` |
| `--theme-name, -t` | Nombre del tema | `plymotion` |
| `--image-dir` | Ruta ImageDir escrita en el theme | `/usr/share/plymouth/themes/<theme-name>` |
| `--install` | Instala el theme generado (usa `installer.py`, pide sudo) | `false` |

Sin `--install`, `convert` imprime al final el comando manual de instalación
equivalente (copiar archivos + `update-alternatives` + `update-initramfs`).

## Probar la conversión rápidamente

No hace falta instalar el theme para ver si la animación "funciona": basta con
generar los frames y abrir la carpeta de salida.

```bash
# 1. Instalar dependencias (una sola vez)
uv sync --all-extras

# 2. Lanzar la GUI
uv run plymotion gui
# Examinar → elegir tu video → Convertir
# El panel "Registro" muestra cada paso; al terminar se habilita
# "Abrir carpeta de salida" para revisar los frames generados.

# — o por CLI, sin GUI —
uv run plymotion convert -i mi_video.mp4 -o ./salida
xdg-open ./salida   # revisa los PNG generados (frame1.png, frame2.png, ...)
```

Si los PNG se ven bien (nítidos, en el orden correcto), la animación
funcionará igual en Plymouth: el `.script` generado simplemente los muestra
en loop. Solo cuando quieras verlo en el arranque real necesitas instalar
(`--install` en el CLI, o el botón "Instalar" en la GUI, ambos piden sudo).

## Seguridad Plymouth

**Plymouth es seguro**: Un theme roto o corrupto NUNCA impide el boot. Plymouth cae en fallback automático a modo texto. El proceso real de boot (systemd/init) continúa sin afectarse.

### Medidas de protección

- **Backup automático**: Se guarda una copia del theme actual antes de sobreescribir
- **Validación**: Se verifican archivos requeridos (.plymouth, .script, frames) antes de instalar
- **Rollback**: Si algo falla, se puede restaurar el theme anterior

### Recuperación si Plymouth falla

Si el boot se ve raro o en negro:

```bash
# Desde el menú GRUB: presionar 'e', agregar al kernel:
plymouth.enable=0

# O desde TTY (Ctrl+Alt+F2):
sudo plymouth-set-default-theme -R text
sudo update-initramfs -u
```

### Test sin reiniciar

```bash
sudo plymouthd --no-daemon --debug
# En otra terminal:
sudo plymouth show-splash
# Para salir (Ctrl+Alt+F3):
sudo plymouth quit
```

## Desarrollo

### Requisitos

- Python 3.10+
- uv
- ffmpeg (para extraer frames de video)

### Comandos de desarrollo

```bash
# Instalar dependencias
uv sync --all-extras

# Tests
uv run pytest tests/ -v

# Linting
uv run ruff check src/ tests/

# Type checking
uv run pyright src/
```

### Estructura del proyecto

```
plymotion/
├── pyproject.toml
├── src/plymotion/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                  # CLI principal (convert, gui)
│   ├── video_extractor.py      # Extracción de frames con ffmpeg
│   ├── frame_processor.py      # Optimización con Pillow
│   ├── template_generator.py   # Generador de .script y .plymouth
│   ├── installer.py            # Instalación segura del theme
│   └── ui/
│       ├── __init__.py
│       ├── app.py              # Ventana principal tkinter
│       └── widgets.py          # Widgets reutilizables
├── tests/
│   ├── test_frame_processor.py
│   ├── test_template_generator.py
│   ├── test_cli.py
│   ├── test_installer.py
│   └── test_ui.py
├── examples/
│   ├── legacy-manual-theme.plymouth  # Theme de referencia escrito a mano
│   └── legacy-manual-theme.script    # (anterior al generador automático)
└── README.md
```

### Arquitectura UI/Lógica

La UI (tkinter) es solo una capa de presentación. Toda la lógica vive en módulos independientes:
- `video_extractor.py` - Extracción de frames
- `frame_processor.py` - Optimización de imágenes
- `template_generator.py` - Generación de archivos Plymouth
- `installer.py` - Instalación segura

Esto permite agregar otras interfaces (web, CLI, etc.) sin modificar la lógica core.

## License

MIT
