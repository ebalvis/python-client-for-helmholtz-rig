# python-client-for-helmholtz-rig

# Helmholtz Control Suite

Este repositorio contiene una suite de software en Python diseñada para controlar remotamente un sistema de generación de campo magnético basado en bobinas de Helmholtz y para recibir datos de telemetría de sensores de un dispositivo Android.

El sistema completo se compone de tres partes que trabajan juntas:

1.  **Servidor de Control (BHC2000 - Delphi)**: Una aplicación de escritorio para Windows que controla directamente tres fuentes de alimentación Wanptek a través de Modbus para generar el campo magnético.
2.  **Servidor de Sensores (Sensor Android SCOA - B4A)**: Una aplicación Android que lee el acelerómetro y el magnetómetro del dispositivo y los transmite por la red.
3.  **Suite de Cliente (Python)**: Este repositorio. Contiene las librerías y scripts para comunicarse con ambos servidores, permitiendo la automatización y el control remoto de todo el sistema.

-----

## Arquitectura del Sistema

El proyecto sigue una arquitectura de cliente-servidor distribuida:

  * **PC de Control (Python)**: Actúa como el cerebro del sistema. Ejecuta los scripts de Python que envían comandos y reciben datos.
      * `wanptek_control.py`: Se conecta por **TCP** al Servidor de Control para ajustar voltajes, corrientes y encender/apagar las fuentes.
      * `read_android_sensor.py`: Se suscribe por **UDP** al Servidor de Sensores para recibir datos de movimiento y campo magnético en tiempo real.
  * **PC de Laboratorio (Delphi)**: Ejecuta la aplicación `BHC2000.exe`, que está conectada físicamente a las fuentes de alimentación por un puerto serie (Modbus RTU). Escucha comandos a través de su servidor TCP integrado.
  * **Dispositivo Móvil (Android)**: Ejecuta la app `Sensor Android SCOA`, que actúa como una unidad de medición inercial (IMU) inalámbrica, enviando sus lecturas por UDP a los clientes suscritos.

-----

## Componentes

### 1\. Servidor de Control: BHC2000 (Delphi)

Aplicación de escritorio que sirve como puente entre la red y el hardware.

  * **Interfaz Gráfica**: Permite el control manual de cada una de las 3 fuentes de alimentación (ejes X, Y, Z).
  * **Comunicación**: Utiliza el protocolo **Modbus RTU** sobre un puerto serie para comunicarse con las fuentes de alimentación.
  * **API Remota**: Implementa un **servidor TCP** en un puerto configurable (por defecto `4444`) que acepta comandos de texto simples para control remoto. Comandos soportados:
      * `PING`: Verifica la conexión.
      * `SET V<canal> <voltaje>`: Fija el voltaje de un canal.
      * `SET I<canal> <corriente>`: Fija la corriente de un canal.
      * `OUT <canal> ON|OFF`: Activa o desactiva la salida de un canal.
      * `GET V|I|P <canal>`: Obtiene el voltaje, corriente o potencia medidos.
      * `READ ALL`: Devuelve el estado completo de los tres canales.
      * `ALL OFF`: Apaga todas las salidas.

### 2\. Servidor de Sensores: Sensor Android SCOA (B4A)

Aplicación para Android que convierte el móvil en un sensor inalámbrico.

  * **Sensores**: Captura datos del **acelerómetro** y **magnetómetro** del dispositivo.
  * **Protocolo de Comunicación**:
    1.  Un cliente se suscribe enviando un mensaje UDP con el texto `HOLA` al puerto **51042** del móvil.
    2.  El servidor añade la IP del cliente a su lista de distribución.
    3.  Cada \~200ms, el servidor envía un paquete **JSON** con los datos de los sensores a todos los clientes suscritos, al puerto de destino **51043**.
  * **Formato de Datos (JSON)**:
    ```json
    {
      "accelerometer": { "x": 1.23, "y": 0.45, "z": 9.81 },
      "magnetometer": { "x": 30.1, "y": -15.6, "z": 22.8 }
    }
    ```

### 3\. Suite de Cliente (Python)

Este repositorio contiene las herramientas para controlar el sistema.

  * **`wanptek_control.py`**: Una librería de cliente orientada a objetos para interactuar con el servidor Delphi.
      * Clase `WanptekClient` que encapsula la lógica de conexión TCP y el envío de comandos.
      * Métodos de alto nivel como `set_voltage(ch, v)`, `get_current(ch)`, etc.
  * **`test_wanptek.py`**: Un script de ejemplo que muestra cómo usar la librería `WanptekClient` para realizar operaciones comunes como leer valores, fijar un voltaje y apagar las fuentes.
  * **`read_android_sensor.py`**: Un script cliente que se registra en el servidor de sensores Android y muestra en consola los datos JSON recibidos en tiempo real.

-----

## Guía de Inicio Rápido

1.  **Configurar Hardware**: Conecta las 3 fuentes de alimentación Wanptek al PC de laboratorio mediante un adaptador USB a RS-485.
2.  **Iniciar Servidor de Control**:
      * Ejecuta `BHC2000.exe` en el PC de laboratorio.
      * Configura el puerto COM, los parámetros serie y las direcciones Modbus de cada fuente.
      * Asegúrate de que el servidor TCP esté activado y anota la dirección IP del PC y el puerto.
3.  **Iniciar Servidor de Sensores**:
      * Instala y ejecuta la APK `Sensor Android SCOA` en un móvil Android.
      * Asegúrate de que el móvil esté en la misma red WiFi que el PC de control.
      * La app mostrará su dirección IP. Anótala.
4.  **Configurar y Ejecutar Clientes Python**:
      * Clona este repositorio en tu PC de control.
      * Abre `wanptek_control.py` o `test_wanptek.py` y modifica la IP y el puerto para que apunten al PC de laboratorio donde corre el servidor Delphi.
      * Abre `read_android_sensor.py` y modifica la `SERVER_IP` para que sea la IP del móvil Android.
      * Ejecuta los scripts:
        ```bash
        # Para controlar las fuentes
        python test_wanptek.py

        # Para ver los datos de los sensores
        python read_android_sensor.py
        ```


