# Plymotion

Convierte cualquier video en una animación de arranque personalizada para tu sistema Linux usando Plymouth.

## Características

- **GUI con Flet**: convertir, instalar, probar sin reiniciar, restaurar backup o volver a modo texto — todo desde la ventana
- **CLI en Python**: para automatización/scripting; la GUI es la forma recomendada de uso interactivo
- **Frame-by-frame**: Extrae frames del video y los convierte en una secuencia de animación
- **Loop infinito**: La animación se repite continuamente durante el boot
- **Optimización automática**: Redimensiona y comprime frames para carga rápida
- **Instalación segura**: Backup automático del theme anterior antes de sobreescribir; cada acción privilegiada pasa por un único prompt gráfico de `pkexec`

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/xenthrall/plymotion.git
cd plymotion

# Instalar con uv
uv sync
```

## Uso

### Interfaz gráfica (recomendado)

```bash
plymotion gui
```

La primera vez descarga el cliente de escritorio de Flet (necesita red);
los siguientes arranques son instantáneos. Flujo completo, sin tocar la
terminal:

1. **Examinar** → elige tu video. Se muestra su resolución/duración original.
2. Ajusta resolución, FPS y nombre del theme.
3. **Convertir** → extrae y optimiza los frames (barra de progreso + registro
   paso a paso).
4. **Instalar** → copia el theme, hace backup del anterior con ese mismo
   nombre, registra el theme con `update-alternatives` y regenera el
   initramfs. Pide un único prompt gráfico de administrador (`pkexec`).
5. **Probar theme instalado** → muestra el splash ya instalado en vivo unos
   segundos (`plymouthd` + `plymouth show-splash`), sin reiniciar.
6. Si algo no te convence: **Restaurar backup** (vuelve a la copia anterior
   de ese theme) o **Volver a modo texto** (fallback seguro garantizado) —
   ambos también piden `pkexec`.

Todas las acciones que tocan el sistema (Instalar, Probar, Restaurar,
Volver a modo texto) muestran antes un diálogo de confirmación explicando
qué va a pasar.

### Línea de comandos (automatización/scripting)

Se mantiene para scripts y CI; para uso interactivo la GUI es más cómoda.

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
| `--install` | Instala el theme generado (usa `installer.py`, pide autenticación gráfica vía `pkexec`) | `false` |

Sin `--install`, `convert` imprime al final el comando manual de instalación
equivalente (copiar archivos + `update-alternatives` + `update-initramfs`).

## Probar la conversión sin GUI

Si solo quieres revisar los frames generados por CLI, sin instalar nada:

```bash
uv run plymotion convert -i mi_video.mp4 -o ./salida
xdg-open ./salida   # revisa los PNG generados (frame1.png, frame2.png, ...)
```

Si los PNG se ven bien (nítidos, en el orden correcto), la animación
funcionará igual en Plymouth: el `.script` generado simplemente los muestra
en loop.

## Seguridad Plymouth

**Plymouth es seguro**: Un theme roto o corrupto NUNCA impide el boot. Plymouth cae en fallback automático a modo texto. El proceso real de boot (systemd/init) continúa sin afectarse.

### Medidas de protección

- **Backup automático**: Se guarda una copia del theme actual antes de sobreescribir
- **Validación**: Se verifican archivos requeridos (.plymouth, .script, frames) antes de instalar
- **Rollback**: Botón "Restaurar backup" en la GUI (o `installer.restore_backup()`) si algo falla

### Recuperación si Plymouth falla

Si el boot se ve raro o en negro, la forma más rápida es el botón **"Volver a
modo texto"** de la GUI la próxima vez que arranques (o `installer.reset_to_default()`).
Si no puedes ni arrancar el sistema:

```bash
# Desde el menú GRUB: presionar 'e', agregar al kernel:
plymouth.enable=0

# O desde TTY (Ctrl+Alt+F2), forzando el theme de texto vía update-alternatives
# (plymouth-set-default-theme no está disponible en todas las distros):
sudo update-alternatives --set default.plymouth /usr/share/plymouth/themes/text/text.plymouth
sudo update-initramfs -u
```

### Test sin reiniciar

El botón **"Probar theme instalado"** de la GUI hace exactamente esto por ti.
Equivalente manual:

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
- polkit/`pkexec` (para instalar/probar/restaurar desde la GUI — viene por
  defecto en GNOME, KDE y la mayoría de entornos de escritorio Linux)

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
│   ├── installer.py            # Instalar/probar/restaurar (todo vía pkexec)
│   └── ui/
│       ├── __init__.py
│       ├── app.py              # Ventana principal Flet
│       └── widgets.py          # Helpers reutilizables (dropdowns, log)
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

La UI ([Flet](https://flet.dev)) es solo una capa de presentación. Toda la lógica vive en módulos independientes:
- `video_extractor.py` - Extracción de frames
- `frame_processor.py` - Optimización de imágenes
- `template_generator.py` - Generación de archivos Plymouth
- `installer.py` - Instalar, probar en vivo, restaurar backup o volver a modo texto (todo vía `pkexec`)

Esto permite agregar otras interfaces (web, CLI, etc.) sin modificar la lógica core.

## License

MIT
