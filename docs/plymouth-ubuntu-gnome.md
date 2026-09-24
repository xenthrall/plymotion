# Plymouth en Ubuntu + GNOME: capacidades, límites reales y factores clave

Investigación de base para que Plymotion personalice el arranque **de la
manera correcta**: entendiendo qué controla Plymouth, qué no, dónde están los
límites de verdad y qué cambia entre distros. Foco actual: **Ubuntu con
GNOME**.

> Complementa a [`plymouth-reference-notes.md`](plymouth-reference-notes.md)
> (bug del nombre del `.plymouth`, loop del contador, preview). Donde este
> documento contradice a aquél, este es más reciente (ver §9).

**Método.** Todo lo marcado como *verificado* se comprobó en una máquina real
(tabla de §1) leyendo los scripts instalados, los binarios, la configuración
de systemd y el journal del arranque, o en el código fuente upstream de
Plymouth (`gitlab.freedesktop.org/plymouth/plymouth`). Lo que es inferencia
está marcado como tal.

---

## 1. Sistema de referencia

| Componente | Valor |
|---|---|
| Distro | Ubuntu 26.04.1 LTS (Resolute Raccoon) |
| Plymouth | `24.004.60+git20250831` (paquete `plymouth`, `plymouth-theme-spinner`, `plymouth-theme-ubuntu-text`, `plymouth-label`) |
| Generador de initramfs | **dracut 110** (no initramfs-tools, ver §4) |
| GNOME | gnome-shell 50.1, gdm3 50.1 |
| Firmware | UEFI, Secure Boot desactivado, **tabla ACPI BGRT presente** (logo del fabricante) |
| GPU | Intel Arrow Lake-P (driver `i915`), pantalla eDP 1920x1200, 34x22 cm |
| Kernel cmdline | `quiet splash ...` |
| GRUB | `GRUB_TIMEOUT_STYLE=hidden`, `GRUB_TIMEOUT=0` |
| Theme por defecto de Ubuntu | `bgrt` (prioridad 110 en `update-alternatives`) |

---

## 2. Dónde vive Plymouth en el arranque

Plymouth no es parte de GNOME ni del kernel: es un **daemon (`plymouthd`)**
que se arranca muy temprano desde el initramfs, dibuja en la pantalla con
DRM/KMS y se retira cuando el display manager (GDM) toma la pantalla.

Línea de tiempo **medida** en el sistema de referencia (`journalctl -b -o
short-monotonic`, `systemd-analyze`):

| t (s desde el kernel) | Evento | Qué se ve |
|---|---|---|
| antes de 0 | Firmware UEFI (7,2 s) + GRUB oculto (1,4 s) | Logo del fabricante (BGRT) |
| 0,63 | Kernel registra `simpledrm` (framebuffer heredado del firmware) | Logo del fabricante |
| 0,77 | `plymouth-start.service` → `plymouthd --mode=boot` + `plymouth show-splash` | **Empieza el splash** |
| 0,79 | Splash visible (`Started plymouth-start.service`) | Theme |
| 1,66 | `plymouth-switch-root` (paso del initramfs al disco real) | Theme (sigue sin cortes) |
| 3,31 | Carga el driver nativo `i915`; Plymouth cambia de renderer | Theme (posible re-inicialización del display) |
| ~4,1 | `plymouthd` avisa a systemd; GDM hace `plymouth deactivate` / `quit --retain-splash` | Último frame congelado → pantalla de login |
| 7,4 | `graphical.target` | GDM |

**Conclusión práctica:** en hardware moderno con SSD, **la animación está en
pantalla unos 3–3,5 segundos** en total. Un video de 10 s nunca se va a ver
completo. Esto condiciona todo el diseño (§6.1).

Detalles relevantes verificados en las unidades de systemd:

- `plymouth-start.service` tiene `ConditionKernelCommandLine=splash` y
  `!nosplash`, `!plymouth.enable=0`: **sin `splash` en el cmdline no hay
  splash gráfico**, da igual el theme.
- `/usr/share/plymouth/plymouthd.defaults` en Ubuntu: `ShowDelay=0`,
  `DeviceTimeout=8`, `UseSimpledrm=1`. Es decir, Ubuntu muestra el splash
  **inmediatamente** y usa `simpledrm` para no esperar al driver de la GPU.
- El mismo theme se usa en **apagado y reinicio** (`plymouth-poweroff`,
  `plymouth-reboot`), pero leído del disco en vivo, no del initramfs.

---

## 3. Qué tiene que ver GNOME (y qué no)

**GNOME no configura Plymouth.** No hay ninguna opción en Configuración de
GNOME para el theme de arranque; se elige a nivel de sistema (§4). La
relación es solo de **traspaso de pantalla**:

- `gdm.service` declara `Conflicts=plymouth-quit.service` y
  `After=plymouth-quit.service`: GDM **reemplaza** el `plymouth quit`
  genérico y se encarga él mismo de retirar Plymouth.
- El binario de GDM contiene `plymouth deactivate`, `plymouth --ping` y
  `plymouth quit --retain-splash` (verificado con `strings`). La secuencia
  es: GDM detecta que Plymouth está activo, lo **desactiva** (deja de
  dibujar), arranca el greeter y al final lo cierra **conservando el último
  contenido de pantalla**. Así no hay pantallazo negro entre splash y login.
- Consecuencia: **el frame que esté visible cuando GDM desactiva Plymouth
  queda congelado** hasta que aparece el login. En un video en loop, ese
  frame es aleatorio.
- Esto forma parte del esfuerzo de *flicker-free boot* (Hans de Goede, Red
  Hat; Fedora 30+): firmware → Plymouth → GDM sin parpadeos. Por eso el theme
  por defecto de Ubuntu es **`bgrt`**: reutiliza el logo del fabricante que
  dibujó el firmware (tabla ACPI BGRT) y pone un spinner encima, de forma que
  el usuario ve una sola imagen continua desde que enciende.

**Lo que NO es Plymouth** (a veces se confunde):

| Pantalla | Quién la dibuja | Cómo se personaliza |
|---|---|---|
| Logo del fabricante al encender | Firmware UEFI | No se puede (salvo BIOS del fabricante) |
| Menú de arranque | GRUB | `/etc/default/grub` (oculto en Ubuntu por defecto) |
| **Animación de arranque/apagado** | **Plymouth** | **Theme de Plymouth ← Plymotion** |
| Pantalla de login | GDM (gnome-shell) | Logo: clave GSettings `org.gnome.login-screen logo` (§3.1, vista **Login** de Plymotion). Resto: theme de gnome-shell de GDM |
| Escritorio | gnome-shell | Configuración de GNOME |

Si algún día Plymotion quiere "continuidad visual" hasta el login, el fondo
de GDM es **otra** personalización distinta (recurso `gnome-shell-theme` de
GDM) con sus propios riesgos; no se hace desde Plymouth.

### 3.1 El logo de la pantalla de login

El logo de Ubuntu que aparece abajo en el login **no es de Plymouth**: lo
dibuja GDM a partir de la clave GSettings `org.gnome.login-screen logo`.
Verificado en Ubuntu 26.04:

- **De dónde sale el logo de Ubuntu:** del override de esquema del paquete
  `ubuntu-settings`,
  `/usr/share/glib-2.0/schemas/10_ubuntu-settings.gschema.override` →
  `logo='/usr/share/pixmaps/ubuntu-logo-text-dark.svg'`. El valor por
  defecto upstream es `''` (sin logo).
- **Cómo lee GDM su configuración:** el perfil dconf del usuario `gdm`
  (`/usr/share/dconf/profile/gdm`) es `user-db:user` +
  `file-db:/var/lib/gdm3/greeter-dconf-defaults`. Esa base se compila con
  `/usr/share/gdm/generate-config` (el `ExecStartPre` de `gdm.service`, así
  que corre **en cada arranque de GDM**) a partir de **todos** los keyfiles
  de `/usr/share/gdm/dconf/`, en orden de nombre:
  `00-upstream-settings`, `90-debian-settings` (enlace a
  `/etc/gdm3/greeter.dconf-defaults`) y cualquier otro que agreguemos.
  Un valor en dconf le gana al override del esquema.
- **Cómo lo dibuja** (`loginDialog.js`, extraído del `libshell` de
  gnome-shell 50): carga el archivo con `load_file_sync(..., -1, -1, ...)`,
  es decir **a su tamaño natural, sin escalar**. Lo centra
  horizontalmente y lo ubica verticalmente con
  `plymouthWatermarkVerticalAlignment = 0.96`, la misma posición que la
  marca de agua del theme `bgrt`, ajustando la escala de Plymouth frente a la de
  Mutter. Está hecho para que el logo del login **coincida exactamente** con
  el que se veía en el splash. El logo de Ubuntu y `spinner/watermark.png`
  miden lo mismo: **187x72 px**.
- **Permisos:** GDM corre como el usuario `gdm`, que no puede leer un
  `/home` con permisos 0750 (el caso por defecto). La imagen tiene que vivir
  fuera de `/home`.
- **Cuándo se ve:** la próxima vez que aparezca el greeter (cerrar sesión o
  reiniciar). La **pantalla de bloqueo** la dibuja la sesión del usuario, no
  GDM, y no usa este logo.

**Cómo lo implementa Plymotion** (`src/plymotion/login_logo.py`, vista
**Login** de la GUI):

1. Redimensiona la imagen elegida para que entre en *alto elegido* (72 px
   por defecto, como el de Ubuntu) x 480 px. Conserva la proporción y la
   transparencia, nunca la agranda y la guarda como PNG.
2. Con un solo `pkexec`: la copia a `/usr/share/plymotion/login-logo.png`,
   escribe el drop-in `/usr/share/gdm/dconf/95-plymotion-logo`:

   ```ini
   [org/gnome/login-screen]
   logo='/usr/share/plymotion/login-logo.png'
   ```

   y ejecuta `generate-config`. El prefijo `95` le gana tanto al override
   de Ubuntu como a un `logo=` que el admin haya puesto en
   `/etc/gdm3/greeter.dconf-defaults`.
3. **Restaurar** = borrar ese archivo y la imagen, y volver a ejecutar
   `generate-config`.

Se eligió un drop-in propio en vez de editar
`/etc/gdm3/greeter.dconf-defaults` porque ese es un conffile del admin:
modificarlo por programa es frágil y deshacerlo sin pisar cambios ajenos
también. dpkg no toca archivos que no son suyos, así que el drop-in
sobrevive a las actualizaciones de `gdm3`.

**Límites:**

- Solo el logo. Fondo, colores y tipografía del login se definen en el
  recurso `gnome-shell-theme.gresource` de GDM, que es mucho más invasivo
  y se rompe con las actualizaciones de gnome-shell.
- El fondo del login es oscuro: conviene un PNG transparente con colores
  claros (el de Ubuntu es la variante `-dark`, texto blanco).
- Si alguien fijó `logo` en la base de usuario del propio `gdm`
  (`user-db`, poco habitual), esa gana sobre el `file-db`.
- Otras distros: Fedora y Debian usan el mismo mecanismo con GDM, pero la
  ruta de keyfiles puede ser distinta (p. ej. `/etc/dconf/db/gdm.d/` +
  `dconf update`). Plymotion hoy solo escribe en la ruta de Ubuntu y
  desactiva la función si `/usr/share/gdm/dconf` no existe.

---

## 4. Cómo elige Ubuntu el theme y cómo llega al initramfs

### 4.1 Selección del theme

Hay **dos** mecanismos y uno tiene prioridad sobre el otro:

1. **`update-alternatives`** (propio de Debian/Ubuntu): el enlace
   `/usr/share/plymouth/themes/default.plymouth` apunta al `.plymouth`
   elegido. Es lo que usa Plymotion. En el sistema de referencia:
   `bgrt` (110) y `mi-theme` (120, activo).
2. **`/etc/plymouth/plymouthd.conf`** con `[Daemon] Theme=<nombre>`
   (mecanismo upstream, el que usa `plymouth-set-default-theme` en
   Fedora/Arch). **Si está definido, gana** tanto al construir el initramfs
   como en ejecución.

> Riesgo para Plymotion: si el usuario (u otra herramienta) dejó `Theme=` en
> `plymouthd.conf`, instalar con `update-alternatives` "funciona" pero el
> arranque sigue mostrando el otro theme. El instalador debería leer ese
> archivo y avisar. (En el sistema de referencia está vacío.)

### 4.2 Ubuntu 26.04 usa dracut, no initramfs-tools

Ubuntu pasó a **dracut** como generador de initramfs por defecto (se decidió
para 25.10; 26.04 LTS es la primera LTS con dracut). Verificado:

- `/usr/sbin/update-initramfs` **pertenece al paquete `dracut`**: es un
  wrapper de compatibilidad ("Taken from initramfs-tools and adapted for
  dracut"). Por eso `update-initramfs -u -k all` de Plymotion sigue
  funcionando.
- `lsinitramfs` es de initramfs-tools; con dracut la herramienta es
  **`lsinitrd`**.
- La configuración está en `/etc/dracut.conf.d/`, no en `/etc/initramfs-tools/`.

El módulo `45plymouth` de dracut llama a
`/usr/libexec/plymouth/plymouth-populate-initrd`, que (verificado leyendo el
script):

1. Lee el theme de `update-alternatives --query default.plymouth` y calcula
   `nombre = basename <ruta> .plymouth`.
2. Busca `themes/<nombre>/<nombre>.plymouth`. **La regla "el archivo se llama
   igual que el directorio" sigue vigente con dracut**, igual que con
   initramfs-tools (bug documentado en las notas anteriores).
3. Lee `ModuleName` (p. ej. `script`) y exige que exista
   `<plugins>/<ModuleName>.so`, si no aborta con error.
4. Copia **el directorio del theme completo, recursivamente**
   (`inst_recur`), y además `ImageDir` si está fuera de él. Todo lo que
   haya en el directorio va al initramfs (incluido nuestro `theme.json`, que
   no hace falta).
5. Copia fuentes (`Font=`, `TitleFont=` del `.plymouth` y la fuente por
   defecto de `fc-match`), los renderers `drm.so`/`frame-buffer.so`, el
   plugin de texto `label-pango.so`, y los servicios de systemd de Plymouth
   (incluido `systemd-ask-password-plymouth`, el puente para pedir
   contraseñas de LUKS).

### 4.3 Qué implica "está en el initramfs"

El arranque (hasta `switch-root`, ~1,7 s) usa **la copia empaquetada**; el
resto y el apagado usan el disco. Por eso un theme puede verse bien en la
preview y en el apagado y aun así fallar al arrancar. Cualquier cambio de
theme **requiere regenerar el initramfs de todos los kernels** (ya lo hace
Plymotion con `-k all`).

Tamaño actual del initramfs de referencia: **41,7 MB**. El theme instalado
(`mi-theme`, 56 frames de 500x500) ocupa 2,9 MB en disco.

---

## 5. Módulos (plugins) de Plymouth

Un theme es un `.plymouth` que elige un **módulo** (`ModuleName=`). Módulos
presentes en Ubuntu 26.04:

| Módulo | Qué hace | Theme de ejemplo |
|---|---|---|
| `two-step` | Animación de frames numerados + spinner + diálogos nativos (contraseña, mensajes, barra de progreso), soporte BGRT, modos de actualización | `bgrt`, `spinner` |
| `script` | **Lenguaje de script propio**: control total de sprites, imágenes y callbacks | Los de Plymotion |
| `text` / `details` / `ubuntu-text` / `tribar` | Modo texto (fallback seguro) | `text`, `details` |

`two-step` es declarativo (se configura con claves en el `.plymouth`) y ya
resuelve bien contraseña, mensajes y BGRT. `script` es más flexible pero
**todo lo que no programes no existe** (§6.5). Plymotion usa `script`.

---

## 6. Límites reales y factores importantes

### 6.1 Tiempo en pantalla

~3–3,5 s en el sistema de referencia (§2). En discos lentos, con LUKS o con
muchos servicios puede ser más, pero **no hay forma de alargarlo** desde el
theme (Plymouth no retrasa el arranque). Recomendación: clips de **2–4 s en
loop**, pensados para que cualquier frame sirva como "último frame
congelado" (§3).

### 6.2 Memoria: los PNG se decodifican enteros

`ply-image.c` carga cada PNG con libpng y lo convierte a un buffer **ARGB32
sin comprimir** (4 bytes por píxel). El script de Plymotion llama a
`Image()` para **todos** los frames al inicio, así que la RAM que usa es:

| Frames | Resolución | RAM decodificada |
|---|---|---|
| 56 (theme actual) | 500x500 | 56 MB |
| 150 | 320x240 | 46 MB |
| 150 | 1920x1080 | **1,2 GB** |
| 300 | 1920x1080 | **2,5 GB** |

La paleta reducida de Plymotion hace chico el archivo en disco, **pero no
ahorra RAM**: una vez decodificado, cada píxel ocupa 4 bytes igual. Una
animación a pantalla completa y larga puede quedarse sin memoria en el
initramfs o tardar mucho en aparecer.

### 6.3 Tiempo hasta el primer frame

Todas las llamadas a `Image()` se ejecutan antes de registrar el callback de
refresco: **el splash no muestra nada hasta decodificar todos los PNG**.
Por esto se revirtió el modo "fullscreen con `Image.Scale()`" (commit
`f0e1a81`). Más frames o más grandes = splash más tardío, y con ~3 s
disponibles cada décima cuenta. *Inferencia:* se podría cargar solo el
primer frame y el resto de forma progresiva dentro del callback; hay que
medirlo.

### 6.4 Velocidad de reproducción: **sí se puede ajustar**

- El plugin `script` llama al callback de refresco a `FRAMES_PER_SECOND = 50`
  por defecto (`plugin.c`), con `sleep_time = 1 / refresh_rate`.
- **Existe `Plymouth.SetRefreshRate(n)`** (`script-lib-plymouth.c`,
  verificado también en el `script.so` instalado). Un theme puede fijar la
  frecuencia a los fps con que se extrajo el video.
- Esto **corrige una suposición del proyecto**: `template_generator.py`
  dice que la tasa es fija a 50 Hz y que un video extraído a 30 fps se ve
  1,67x más rápido. Con `Plymouth.SetRefreshRate(fps)` en el script
  generado, la velocidad coincidiría con el video original.

### 6.5 Contraseña de disco (LUKS) y mensajes

Con `script`, **Plymouth no dibuja nada por su cuenta**: si el theme no
registra los callbacks, la petición de contraseña de LUKS llega (vía
`systemd-ask-password-plymouth`) pero **no se ve el campo en pantalla**. El
usuario tiene que escribir a ciegas o no sabe que se le está pidiendo.

Callbacks disponibles (verificados en el código y en el binario):

| Callback | Para qué |
|---|---|
| `Plymouth.SetDisplayPasswordFunction(fun(prompt, bullets))` | Pedir contraseña (LUKS) |
| `Plymouth.SetDisplayQuestionFunction(fun(prompt, entry))` | Pregunta con texto visible |
| `Plymouth.SetDisplayPromptFunction` | Variante de prompt |
| `Plymouth.SetDisplayNormalFunction(fun())` | Volver al modo normal (ocultar diálogo) |
| `Plymouth.SetDisplayMessageFunction(fun(text))` / `SetHideMessageFunction` | Mensajes del sistema (fsck, errores) |
| `Plymouth.SetBootProgressFunction(fun(time, progress))` | Progreso estimado del arranque |
| `Plymouth.SetUpdateStatusFunction(fun(status))` | Estado de servicios |
| `Plymouth.SetSystemUpdateFunction(fun(progress))` | Modo actualizaciones offline |
| `Plymouth.SetRootMountedFunction(fun())` | Se montó la raíz real |
| `Plymouth.SetKeyboardInputFunction` / `SetValidateInputFunction` | Teclado |
| `Plymouth.SetQuitFunction(fun())` | Plymouth se está cerrando |
| `Plymouth.SetDisplayHotplugFunction` | Se conectó/cambió una pantalla |
| `Plymouth.GetMode()` | `"boot"`, `"shutdown"`, `"reboot"`, `"updates"`, `"system-upgrade"`, `"firmware-upgrade"`, `"system-reset"` |
| `Plymouth.GetCapslockState()` | Aviso de Bloq Mayús |

Para dibujar texto: `Image.Text(texto, r, g, b, a, fuente, alineación)`,
que depende de `label-pango.so` y de fuentes presentes en el initramfs
(dracut las copia, §4.2).

**Esta es la carencia más importante de los themes actuales de Plymotion**
para usuarios con disco cifrado.

### 6.6 Pantallas, resolución y HiDPI

- `Window.GetWidth()` / `GetHeight()` sin argumento devuelven el **máximo**
  entre todas las pantallas; con índice (`Window.GetWidth(0)`) devuelven los
  de una pantalla concreta. `Window.GetX(i)`/`GetY(i)` dan su posición. Con
  varios monitores de distinta resolución, centrar con el máximo no centra
  en cada uno.
- **Escala HiDPI automática** (`ply-utils.c`, constantes copiadas de
  Mutter): se calcula el DPI físico con el EDID; si supera ~1,625x el DPI
  objetivo (135 en portátiles, 110 en pantallas ≥20"), Plymouth usa escala
  2 y **las imágenes se ven al doble de tamaño**. En el sistema de
  referencia: ~142 DPI → escala 1. Se puede forzar con `DeviceScale=` en
  `plymouthd.conf` o con `plymouth.force-scale=` en el cmdline.
- **Cambio de renderer:** Plymouth empieza con `simpledrm` (resolución que
  dejó el firmware) y pasa al driver nativo (`i915` a los 3,3 s). Si la
  resolución cambia, las posiciones calculadas una sola vez al inicio pueden
  quedar descentradas. *Inferencia:* recalcular la posición en
  `SetDisplayHotplugFunction` o en el propio refresco lo evitaría.

### 6.7 Formato de imagen y fondo

- Formato soportado para themes: **PNG** (el cargador de BMP es para la
  imagen BGRT del firmware).
- `Window.SetBackgroundTopColor(r,g,b)` / `SetBackgroundBottomColor` (valores
  0–1) pintan el fondo con un color sólido o degradado; lo que no cubre el
  sprite queda de ese color (negro si no se define).
- `Sprite.SetOpacity`, `SetZ`, `Image.Scale/Rotate/Crop/Tile` permiten
  composición, pero **cada operación sobre imágenes cuesta CPU en un momento
  en que el sistema está arrancando**.

### 6.8 Seguridad y recuperación

- Un theme roto **no impide arrancar**: Plymouth cae a modo texto y
  systemd sigue. Verificado indirectamente por el bug del nombre (§4.2).
- Con `GRUB_TIMEOUT=0` y menú oculto, para llegar a GRUB hay que pulsar
  `Esc` (UEFI) o mantener `Shift` (BIOS) al arrancar, y ahí añadir
  `plymouth.enable=0` o quitar `splash`.
- Parámetros de kernel útiles (extraídos del binario): `plymouth.enable=0`,
  `nosplash`, `plymouth.debug` (log en `/var/log/plymouth-debug.log`),
  `plymouth.force-scale=`, `plymouth.splash-delay=`,
  `plymouth.use-simpledrm=`, `plymouth.ignore-serial-consoles`.
- Claves de `plymouthd.conf`: `Theme`, `ThemeDir`, `ShowDelay`,
  `DeviceTimeout`, `DeviceScale`, `UseSimpledrm`.

---

## 7. ¿Cambia por distro? Sí, en la instalación; poco en el theme

El **formato del theme** (`.plymouth` + módulo `script` + imágenes) es el
mismo en todas partes porque todos usan Plymouth upstream. Lo que cambia es
**cómo se selecciona el theme y cómo se reconstruye el initramfs**:

| Distro | Selección del theme | Initramfs | Theme por defecto |
|---|---|---|---|
| Ubuntu ≤ 24.04 / Debian | `update-alternatives` (`default.plymouth`) | initramfs-tools: `update-initramfs -u -k all`, ver con `lsinitramfs` | `bgrt` (Ubuntu); en Debian lo define `desktop-base` según la versión |
| **Ubuntu 25.10 / 26.04** | `update-alternatives` (+ `plymouthd.conf` si tiene `Theme=`) | **dracut**, con wrapper `update-initramfs`; ver con `lsinitrd` | `bgrt` |
| Fedora | `plymouth-set-default-theme <nombre> -R` (escribe `plymouthd.conf`) | dracut (`-R` lo reconstruye) | `bgrt` |
| Arch | `plymouth-set-default-theme -R <nombre>` + hook `plymouth` en `mkinitcpio.conf` | mkinitcpio | ninguno hasta configurarlo |

**Para Ubuntu + GNOME** el camino actual de Plymotion
(`update-alternatives` + `update-initramfs -u -k all`) **es correcto tanto en
24.04 como en 26.04**, gracias al wrapper. Lo que hay que ajustar son los
comandos de verificación (`lsinitrd` en vez de `lsinitramfs`) y la
comprobación de `plymouthd.conf`.

---

## 8. Comandos de verificación (Ubuntu 26.04)

```bash
# ¿Qué theme está seleccionado?
update-alternatives --query default.plymouth
grep -v '^#' /etc/plymouth/plymouthd.conf        # ¿hay un Theme= que lo pise?

# ¿El theme quedó realmente dentro del initramfs? (dracut)
sudo lsinitrd /boot/initrd.img-$(uname -r) | grep -E 'plymouth/themes/|script\.so'

# ¿Cuánto tiempo estuvo el splash en pantalla en este arranque?
journalctl -b -o short-monotonic | grep -iE 'plymouth|gdm'
systemd-analyze

# Preview en vivo (sin reiniciar)
sudo plymouthd --no-daemon --debug & sleep 1
sudo plymouth show-splash; sleep 5; sudo plymouth quit

# Probar el diálogo de contraseña durante la preview
sudo plymouth ask-for-password --prompt "Contraseña del disco"
sudo plymouth display-message --text "Mensaje de prueba"

# Logo del login (GDM)
cat /usr/share/gdm/dconf/95-plymotion-logo 2>/dev/null   # ¿hay logo de Plymotion?
grep -h logo /usr/share/glib-2.0/schemas/*.override       # logo de la distro
strings /var/lib/gdm3/greeter-dconf-defaults | grep -A1 login-screen   # base compilada
```

---

## 9. Correcciones a supuestos previos del proyecto

| Supuesto | Realidad verificada |
|---|---|
| "Ubuntu usa initramfs-tools; verificar con `lsinitramfs`" | En 26.04 es **dracut**; `update-initramfs` es un wrapper; se verifica con `lsinitrd`. La regla del nombre del `.plymouth` sigue aplicando (`plymouth-populate-initrd`). |
| "Plymouth refresca a 50 Hz fijos, independiente de los fps" | 50 Hz es el valor **por defecto**; `Plymouth.SetRefreshRate()` lo cambia. |
| "Frames más livianos = menos costo" | Solo en disco/initramfs. En RAM cada frame ocupa `ancho × alto × 4` bytes. |
| "El theme se selecciona con update-alternatives" | Es cierto, pero `Theme=` en `/etc/plymouth/plymouthd.conf` tiene prioridad. |

---

## 10. Implicaciones para Plymotion (priorizadas)

1. **Callbacks de contraseña/mensajes** en el script generado (§6.5): sin
   esto el theme es inseguro de usar con LUKS. Es lo más importante.
2. **`Plymouth.SetRefreshRate(fps)`** en el script para que la velocidad
   coincida con el video (§6.4), y actualizar `estimate_loop_seconds`.
3. **Presupuesto de recursos en la UI**: mostrar RAM decodificada
   (`frames × w × h × 4`) y duración real vs ~3 s en pantalla; avisar en
   límites razonables (§6.1–6.3).
4. **Color de fondo** configurable con `Window.SetBackgroundTopColor`
   (§6.7), p. ej. muestreado del borde del video.
5. **Centrado robusto**: recalcular posición por pantalla y ante hotplug o
   cambio de renderer (§6.6).
6. **Instalador**: avisar si `plymouthd.conf` tiene `Theme=` (§4.1); no
   copiar `theme.json` al directorio del sistema (§4.2); verificar tras
   instalar que el theme está en el initramfs (`lsinitrd`) (§8).
7. **Opción "sobre BGRT"** (a futuro): generar un theme `two-step` con
   `UseFirmwareBackground=true` y la animación como spinner, para mantener
   el flicker-free boot de GNOME con el logo del fabricante (§3).
8. Soporte Fedora/Arch: fuera del foco actual; el theme generado ya es
   portable, solo cambiaría el instalador (§7).

---

## Fuentes

- Código fuente de Plymouth: `src/plugins/splash/script/`
  (`script-lib-plymouth.c`, `script-lib-sprite.c`, `plugin.c`, `*.script`),
  `src/libply/ply-utils.c` (escala HiDPI),
  `src/libply-splash-graphics/ply-image.c` —
  <https://gitlab.freedesktop.org/plymouth/plymouth>
- Archivos instalados en el sistema de referencia:
  `/usr/lib/dracut/modules.d/45plymouth/module-setup.sh`,
  `/usr/libexec/plymouth/plymouth-populate-initrd`,
  `/usr/sbin/update-initramfs`, `/usr/share/plymouth/plymouthd.defaults`,
  `/usr/lib/systemd/system/{plymouth-*,gdm}.service`,
  `/usr/share/plymouth/themes/{bgrt,spinner}/*.plymouth`.
- Login de GDM: `/usr/share/gdm/generate-config`, `/usr/share/gdm/dconf/`,
  `/usr/share/dconf/profile/gdm`,
  `/usr/share/glib-2.0/schemas/org.gnome.login-screen.gschema.xml` y
  `10_ubuntu-settings.gschema.override`, y
  `/org/gnome/shell/gdm/loginDialog.js` (extraído con `gresource` de
  `/usr/lib/gnome-shell/libshell-18.so`).
- [Spec: Switch to Dracut — Ubuntu Community Hub](https://discourse.ubuntu.com/t/spec-switch-to-dracut/54776)
- [Ubuntu Switches to Dracut With 25.10 — It's FOSS](https://itsfoss.com/news/ubuntu-switches-to-dracut/)
- [How to Configure Dracut Initramfs on Ubuntu 26.04 — LinuxConfig](https://linuxconfig.org/how-to-configure-dracut-initramfs-on-ubuntu-26-04)
- [Changes/FlickerFreeBoot — Fedora Project Wiki](https://fedoraproject.org/wiki/Changes/FlickerFreeBoot)
- [Plymouth Lands Its Tighter Integration With UEFI Flicker-Free Boot — Phoronix](https://www.phoronix.com/news/Plymouth-ACPI-BGRT-Support)
- [Flicker Free Boot — Gentoo Wiki](https://wiki.gentoo.org/wiki/Flicker_Free_Boot)
- [no smooth transition plymouth -> gdm (#890) — GNOME GitLab](https://gitlab.gnome.org/GNOME/gdm/-/work_items/890)
