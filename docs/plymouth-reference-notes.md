# Notas técnicas sobre temas Plymouth basados en frames

Este documento resume conocimiento práctico sobre cómo funcionan los temas
Plymouth de tipo "animación por frames" (el mismo enfoque que usa
`plymotion`), y cómo se instalan/prueban en distintas distros.

## 1. Estructura de un tema Plymouth basado en script

- `*.plymouth`: define `Name`, `Description`, `ModuleName=script`, y en la
  sección `[script]` el `ImageDir` y `ScriptFile`. Coincide con el formato
  que genera `template_generator.py`.
- `*.script`: carga un array de `Image()` (una por frame), crea un `Sprite`
  centrado con `Window.GetWidth()/GetHeight()`, y usa
  `Plymouth.SetRefreshFunction()` para animar cambiando `sprite.SetImage()`
  en cada callback.

## 2. El reseteo del contador de frames es crítico

Un error común en este tipo de scripts es incrementar el contador de frame
en el callback de refresco sin resetearlo al llegar al final del array:

```
fun refresh_callback () {
  sprite.SetImage(image_arr[count]);
  ...
  count += 1;
}
```

Sin el reseteo, la animación se congela (o produce errores de índice) al
llegar al último frame, en vez de reiniciar el boot splash en loop. Nuestro
`template_generator.py` (`SCRIPT_TEMPLATE`) ya lo hace correctamente:

```
count++;
if (count >= $frame_count) {
  count = 0;
}
```

Vale la pena mantener una prueba explícita de este comportamiento (ver
`tests/test_template_generator.py`) para no regresarlo por accidente.

## 3. Truco de "velocidad de animación" saltando frames

En vez de generar dos sets de imágenes o cambiar el framerate de Plymouth,
la velocidad percibida de la animación se puede controlar con **cuánto
avanza el contador por refresco**:

- Rápido: `count += 2;` (usa la mitad de los frames)
- Normal/lento: `count += 1;` (usa todos los frames)

**Idea aprovechable:** `frame_processor.py`/`template_generator.py` podrían
exponer un parámetro de "salto de frames" (`step`) que module la velocidad
percibida de la animación sin re-extraer video, generando variantes
rápida/lenta con el mismo set de imágenes cambiando solo el `.script`. Es
una optimización menor, no urgente.

## 4. Instalación por distro (relevante para `installer.py`)

Nuestro `installer.py` actual solo hace `update-alternatives` +
`update-initramfs -u`, que es específico de Debian/Ubuntu. El registro del
tema y la regeneración de la initramfs varían por distro:

| Distro | Registrar tema | Regenerar initramfs |
|---|---|---|
| Ubuntu/Debian | `update-alternatives --install .../default.plymouth default.plymouth <ruta .plymouth> <priority>` seguido de `update-alternatives --config default.plymouth` | `update-initramfs -u` |
| Fedora | `plymouth-set-default-theme <nombre-tema> -R` (requiere el paquete `plymouth-theme-script`) | `dracut --force` |
| Arch Linux | `plymouth-set-default-theme -R <nombre-tema>` (requiere habilitar `plymouth-start.service` si no estaba instalado) | El propio `-R` de `plymouth-set-default-theme` ya reconstruye la initramfs en Arch |

**Aprovechable directamente:** si `plymotion` quiere soportar Fedora/Arch
además de Ubuntu/Debian, `installer.py` necesitaría detectar la distro
(leyendo `/etc/os-release`) y ramificar entre:
- `update-initramfs -u` (Debian/Ubuntu),
- `dracut --force` (Fedora),
- el propio `plymouth-set-default-theme -R` que ya cubre initramfs en Arch.

Actualmente `install_theme()` en `src/plymotion/installer.py:70-103` asume
siempre `update-initramfs -u`, lo que rompería silenciosamente en Fedora/Arch
(el comando no existe ahí). Vale la pena añadir detección de distro o al
menos documentar la limitación.

## 5. Preview / testing sin reiniciar

Dos formas de probar un tema en vivo:

- Manual (2 terminales):
  ```bash
  sudo plymouthd --no-daemon --debug     # terminal 1
  sudo plymouth show-splash              # terminal 2
  sudo plymouth quit                     # para salir
  ```
- Simulando eventos de progreso de boot mientras se previsualiza:
  ```bash
  plymouthd
  plymouth --show-splash
  for ((I=0; I<$DURATION; I++)); do
    plymouth --update=test$I
    sleep 1
  done
  plymouth quit
  ```
  `plymouth --update=<mensaje>` sirve para simular actualizaciones de
  estado del boot, algo que nuestro `preview_installed_theme()` no ejercita
  actualmente (solo hace `sleep`). Podría ser útil como mejora futura para
  probar que el tema reacciona bien a esos eventos, no solo a la animación
  en loop.

  Nuestra versión de `preview_installed_theme()` ya es más robusta en un
  aspecto importante: guarda el PID de `plymouthd` y hace `wait` sobre él
  en vez de un `killall plymouthd` a ciegas (que mataría cualquier
  instancia de plymouthd en el sistema).

## Resumen de acciones potenciales para `plymotion`

1. (Opcional, bajo impacto) Añadir detección de distro en `installer.py`
   para elegir entre `update-initramfs -u` / `dracut --force` / el `-R` de
   Arch, si se quiere soportar Fedora/Arch además de Debian/Ubuntu.
2. (Opcional, bajo impacto) Considerar exponer un parámetro de "salto de
   frames" para variantes rápida/lenta de la animación sin duplicar el
   set de imágenes.
3. Sin cambios necesarios en la lógica de looping del `.script`: ya es
   correcta y robusta; mantenerla cubierta por tests.
