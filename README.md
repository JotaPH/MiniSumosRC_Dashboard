# MiniSumos RC Dashboard local

Servidor web local con Flask para mostrar el marcador y registrar ataques desde teléfonos conectados a la misma red.

## Instalar y ejecutar (Windows)

```powershell
py -m pip install -r requirements.txt
py app.py
```

En el computador abre http://localhost:8000. Para acceder desde los celulares, ejecuta `ipconfig`, identifica la IPv4 del adaptador de la red compartida y abre `http://IP-DEL-COMPUTADOR:8000`.

## Vistas
- **Visualización:** marcador general y controles básicos de demostración.
- **Ataques 1:** muestra solo el nombre del robot 1, el contador grande, el botón grande para sumar y el botón secundario para restar.
- **Ataques 2:** la misma vista para el robot 2.
- Restar no permite que el contador sea menor que cero.
- Los cambios se reflejan en los dispositivos conectados mediante actualización automática.

## Importante
Este es un prototipo independiente. Aún no está conectado a la ESP32 ni a la base de datos de la aplicación de escritorio. Los niveles son vistas seleccionables, no permisos seguros; antes de usarlo en un torneo real hay que implementar autenticación y persistencia.
