# Bot de Monitoreo de Canal de Empresa Eléctrica para seguir apagones en Telegram

Este bot desarrollado en Python utiliza la librería [Telethon](https://github.com/LonamiWebs/Telethon) para escuchar mensajes en un canal de Telegram, extraer información sobre afectaciones eléctricas (circuitos afectados y restablecidos), y almacenar los datos en una base de datos PostgreSQL. Posteriormente, publica un resumen en un grupo designado.

---

## Funcionalidad

- Escucha mensajes en tiempo real desde un canal de Telegram (`informateessp`).
- Extrae:
  - Circuitos afectados y restablecidos (`121`, `117`, `113`, `112`)
  - Hora del mensaje y hora estimada de afectación/restablecimiento
  - Tiempo aproximado de afectación
- Guarda los eventos en una base de datos PostgreSQL.
- Publica un resumen al grupo configurado.
- Reenvía el mensaje completo si encuentra circuitos de interés pero no puede extraer datos.

---

## Requisitos

- Python 3.8+
- PostgreSQL
- API ID y API HASH de Telegram
- Un canal del cual obtener los mensajes (ej. `@informateessp`)
- Un grupo de Telegram donde enviar los resúmenes

---

## Instalación

```bash
git clone https://github.com/plinkr/eess_info_telegram_bot_parser.git
cd eess_info_telegram_bot_parser
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Archivo `requirements.txt` **

```txt
telethon
asyncpg
python-dateutil
```

------

## Configuración de entorno

Crea un archivo `.env` con las siguientes variables:

```env
API_ID=TU_API_ID
API_HASH=TU_API_HASH
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/tu_basededatos
GRUPO_ID=-123456789  # ID del grupo donde se enviarán los mensajes
```

> Puedes obtener tu `API_ID` y `API_HASH` desde tus Apps en [my.telegram.org](https://my.telegram.org/apps).

------

## Uso

```bash
python eess_info_telegram_bot_parser.py
```

El bot:

- Inicializa la base de datos si no existe.
- Escucha nuevos mensajes en el canal indicado.
- Procesa y extrae la información.
- Publica resúmenes en el grupo destino.

------

## Estructura de la Tabla

Tabla: `movimientos_apagones`

| Campo           | Tipo        | Descripción                                       |
| --------------- | ----------- | ------------------------------------------------- |
| id              | SERIAL      | Clave primaria                                    |
| circuito        | VARCHAR(3)  | Código del circuito (ej. "121")                   |
| tipo            | VARCHAR(20) | Tipo de evento: `afectación` o `restablecimiento` |
| hora_mensaje    | TIMESTAMP   | Fecha/hora en que se recibió el mensaje           |
| hora_programada | TIMESTAMP   | Hora programada del evento (si se detecta)        |
| hora_hasta      | TIMESTAMP   | Hora hasta la cual durará el apagón (si aplica)   |

------

## Notas Técnicas

- Usa expresiones regulares para extraer datos relevantes.
- Agrupa circuitos en pares (`121 y 117`, `113 y 112`) si aparecen juntos.
- Separa y guarda eventos individualmente en la base de datos.
- Asíncrono y eficiente gracias a `asyncpg` y `Telethon`.

------

## Contribuciones

¡Se agradecen sugerencias, pull requests y mejoras! Si encuentras errores o tienes ideas para funcionalidades nuevas, no dudes en abrir un issue.

------

## Licencia

Este proyecto se distribuye bajo la [licencia MIT](LICENSE).


