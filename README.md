# Plymotion 🎬

Plymotion es un tema/plantilla para **Plymouth** que te permite transformar cualquier video en una animación de arranque *frame-by-frame* para tu sistema Linux. Dale un toque personal y dinámico a la pantalla de inicio de tu distribución.

-----

## ✨ Características

  - **Fácil de usar**: Convierte cualquier video en una secuencia de imágenes y úsalo como animación.
  - **Personalizable**: Control total sobre la animación que se muestra al arrancar el sistema.
  - **Ligero**: Basado en el motor de scripting de Plymouth para un rendimiento óptimo.

-----

## 🚀 Instalación en Ubuntu y derivados

Sigue estos pasos para instalar y configurar Plymotion en tu sistema.

### 1\. Clonar el repositorio

Primero, clona este repositorio directamente en el directorio de temas de Plymouth.

```bash
cd /usr/share/plymouth/themes
sudo git clone https://github.com/xenthrall/plymotion.git
```

### 2\. Instalar el tema

Usa `update-alternatives` para que el sistema reconozca Plymotion como una opción de tema de arranque.

```bash
sudo update-alternatives --install \
/usr/share/plymouth/themes/default.plymouth default.plymouth \
/usr/share/plymouth/themes/plymotion/plymotion.plymouth 120
```

*(El `120` al final establece una alta prioridad para este tema).*

### 3\. Seleccionar el tema

Ejecuta el siguiente comando para abrir un menú interactivo donde podrás seleccionar `plymotion.plymouth` de la lista.

```bash
sudo update-alternatives --config default.plymouth
```

### 4\. Actualizar la imagen de arranque (initramfs)

Aplica los cambios al disco de arranque para que se carguen en el próximo inicio.

```bash
sudo update-initramfs -u
```

### 5\. Reiniciar

¡Todo listo\! Reinicia tu sistema para ver la nueva animación en acción.

```bash
sudo reboot
```

-----

## 🛠️ Desarrollo y Pruebas

Si quieres modificar el tema o probarlo sin reiniciar, puedes usar los siguientes métodos.

### Método 1 – Ejecución manual de Plymouth

Este método te permite ver el tema a pantalla completa tal como se vería en el arranque.

1.  **Inicia el demonio de Plymouth** en una terminal:

    ```bash
    sudo plymouthd --no-daemon --debug
    ```

2.  En **otra terminal**, ejecuta el comando para mostrar la animación:

    ```bash
    sudo plymouth show-splash
    ```

3.  ⚠️ **Para salir**, la pantalla quedará bloqueada por Plymouth. Cambia a otra TTY (consola de texto) con **`Ctrl+Alt+F3`** y ejecuta:

    ```bash
    sudo plymouth quit
    ```

4.  Vuelve a tu entorno gráfico con **`Ctrl+Alt+F1`** o **`Ctrl+Alt+F2`**.

### Método 2 – Test rápido (10 segundos)

Este es un método más sencillo para una previsualización rápida.

1.  **Copia el tema** (si no lo clonaste directamente en el directorio de temas):

    ```bash
    sudo cp -r ~/ruta/a/plymotion /usr/share/plymouth/themes/
    ```

2.  **Ejecuta el test**:
    Este comando mostrará la animación durante 10 segundos y se cerrará automáticamente.

    ```bash
    sudo plymouthd ; sudo plymouth --show-splash ; sleep 10 ; sudo plymouth --quit
    ```