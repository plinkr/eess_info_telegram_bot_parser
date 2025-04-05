import asyncio
import os
import re
from datetime import datetime, date, time

import asyncpg
import dateutil
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel

# Credenciales de la API de Telegram
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CANAL_ID = 1579333735  # ID numérico del canal "informateessp"
# CANAL_ID = 2436767198  # ID numérico del canal "plinkr_oss"
GRUPO_ID = int(os.getenv("GRUPO_ID"))  # ID del grupo destino

client = TelegramClient("bot_session", API_ID, API_HASH)


async def init_db():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS movimientos_apagones (
            id SERIAL PRIMARY KEY,
            circuito VARCHAR(3) NOT NULL,
            tipo VARCHAR(20) NOT NULL,
            hora_mensaje TIMESTAMP NOT NULL,
            hora_programada TIMESTAMP,
            hora_hasta TIMESTAMP
        )
    ''')
    await conn.close()


async def guardar_datos(circuito, tipo, hora_mensaje, hora_programada, hora_hasta):
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    await conn.execute('''
        INSERT INTO movimientos_apagones(circuito, tipo, hora_mensaje, hora_programada, hora_hasta)
        VALUES($1, $2, $3, $4, $5)
    ''', circuito, tipo, hora_mensaje, hora_programada, hora_hasta)
    await conn.close()


def extraer_info(mensaje: str):
    """
    Extrae la hora, los circuitos a afectar y a restablecer, y el tiempo aproximado de afectación.
    Se separa el mensaje en dos bloques (afectar y restablecer) y se busca la hora en el mensaje.
    Si no se encuentra hora, se asigna "Hora no encontrada".
    """

    # Buscar la hora en el mensaje (ej: "Para las 8:55 am" o "Para las 12:00 m")
    hora_match = re.search(r"Para las?\s*(\d{1,2}:\d{2})\s*(am|pm|m)?", mensaje, re.IGNORECASE)
    hora = "Hora no encontrada"

    if hora_match:
        hora_str = hora_match.group(1)
        sufijo = (hora_match.group(2) or "").lower()

        if sufijo == "m":
            sufijo = "pm"

        try:
            if sufijo in ("am", "pm"):
                hora_dt = datetime.strptime(f"{hora_str} {sufijo}", "%I:%M %p")
            else:
                # Si no hay sufijo, intentar parsear como 24h
                hora_dt = datetime.strptime(hora_str, "%H:%M")
            # Formatear la hora en formato 12h con AM/PM
            hora = hora_dt.strftime("%I:%M %p")
        except ValueError:
            hora = "Hora no encontrada"

    # Extraer bloque de afectar
    affect_block = ""
    match_afect = re.search(
        r"(Se\s+va\s+a\s+afectar.*?:)(.*?)(?=(Se\s+(?:va\s+a\s+)?restablecer?|Tiempo aproximado de afectación|Nota:)|$)",
        mensaje, re.IGNORECASE | re.DOTALL)
    if match_afect:
        affect_block = match_afect.group(2)

    # Extraer bloque de restablecer
    # Se permite tanto "Se va a restablecer" como "Se restablece"
    rest_block = ""
    match_rest = re.search(
        r"(Se\s+(?:va\s+a\s+)?restablecer?.*?:)(.*?)(?=(Tiempo aproximado de afectación|Nota:)|$)",
        mensaje, re.IGNORECASE | re.DOTALL)
    if match_rest:
        rest_block = match_rest.group(2)

    # Extraer el tiempo aproximado
    tiempo_match = re.search(r"Tiempo aproximado de afectación hasta\s*([^.\n]+)", mensaje, re.IGNORECASE)
    tiempo = tiempo_match.group(0) if tiempo_match else ""

    # Circuitos de interés
    circuits_interes = ["121", "117", "113", "112"]
    afectados = set()
    restablecidos = set()

    # Buscar en el bloque de afectar y el bloque de restablecer
    for circuito in circuits_interes:
        if re.search(r"\b" + re.escape(circuito) + r"\b", affect_block):
            afectados.add(circuito)
        if re.search(r"\b" + re.escape(circuito) + r"\b", rest_block):
            restablecidos.add(circuito)

    return hora, afectados, restablecidos, tiempo


def agrupar_circuitos(circuitos_set):
    """
    Agrupa los circuitos solo si ambos están presentes en el bloque.
    Si se detecta solo uno, se reporta ese circuito individualmente.
      - Grupo 121 y 117
      - Grupo 113 y 112
    """
    grupos = []
    # Grupo 121 y 117
    grupo_121_117 = {"121", "117"}
    presentes_121_117 = grupo_121_117.intersection(circuitos_set)
    if len(presentes_121_117) == 2:
        grupos.append("121 y 117")
    elif len(presentes_121_117) == 1:
        grupos.append(next(iter(presentes_121_117)))

    # Grupo 113 y 112
    grupo_113_112 = {"113", "112"}
    presentes_113_112 = grupo_113_112.intersection(circuitos_set)
    if len(presentes_113_112) == 2:
        grupos.append("113 y 112")
    elif len(presentes_113_112) == 1:
        grupos.append(next(iter(presentes_113_112)))

    return grupos


def extraer_hora_hasta(tiempo: str):
    """
    Extrae y convierte la hora del texto 'Tiempo aproximado de afectación hasta las 9:00 pm' en un objeto datetime.time.
    Si no se puede extraer la hora, devuelve None.
    """
    # Buscar hora con AM/PM
    match = re.search(r"hasta\s+las?\s+(\d{1,2}:\d{2})\s*(am|pm|m)?", tiempo, re.IGNORECASE)
    if match:
        hora_str = match.group(1).strip().lower()
        sufijo = (match.group(2) or "").lower()

        if sufijo == "m":
            sufijo = "pm"
        try:
            if sufijo in ("am", "pm"):
                hora_dt = datetime.strptime(f"{hora_str} {sufijo}", "%I:%M %p")
                return hora_dt.time()
            else:
                # Si no hay sufijo, intentar parsear como 24h
                hora_dt = datetime.strptime(hora_str, "%H:%M")
                return hora_dt.time()
        except ValueError as e:
            print(f"Error al parsear la hora: {e}")
            return None


# Combina la fecha de hoy con la hora obtenida
def combinar_fecha_hora(hora_time: time):
    return datetime.combine(date.today(), hora_time)


@client.on(events.NewMessage(chats=[PeerChannel(CANAL_ID)]))
async def handler(event):
    mensaje = event.raw_text
    print(f"Mensaje recibido: {mensaje}")  # Para depuración
    hora_mensaje = datetime.now()  # Hora de recepción del mensaje
    hora, afectados, restablecidos, tiempo = extraer_info(mensaje)

    # Convertir la hora extraída (si la tienes) a datetime (usando dateutil.parser, por ejemplo)
    try:
        hora_programada = dateutil.parser.parse(hora)
    except Exception:
        hora_programada = None

    # Si en "tiempo" extraes algo como "Tiempo aproximado de afectación hasta  las 10:30 pm", lo parseas también
    hora_hasta = extraer_hora_hasta(tiempo)
    hora_hasta_dt = combinar_fecha_hora(hora_hasta) if hora_hasta else None

    # Agrupar circuitos y guardar cada uno por separado
    grupos_afectados = agrupar_circuitos(afectados)
    grupos_restablecidos = agrupar_circuitos(restablecidos)

    # Lista para ir guardando las tareas que se ejecutarán en segundo plano
    tasks = []

    for grupo in grupos_afectados:
        # Guarda para cada circuito del grupo, suponiendo que el grupo "121 y 117" se quiere separar
        for circuito in grupo.split(" y "):
            tasks.append(asyncio.create_task(
                guardar_datos(circuito, "afectación", hora_mensaje, hora_programada, hora_hasta_dt)
            ))

    for grupo in grupos_restablecidos:
        for circuito in grupo.split(" y "):
            tasks.append(asyncio.create_task(
                guardar_datos(circuito, "restablecimiento", hora_mensaje, hora_programada, None)
            ))

    # Enviar mensaje lo antes posible, sin esperar por guardar_datos
    if grupos_afectados or grupos_restablecidos:
        resumen = f"{hora} - "
        if grupos_afectados:
            resumen += f"Se van a afectar los circuitos: {', '.join(grupos_afectados)}."
            if tiempo:
                resumen += f" {tiempo}."
        if grupos_restablecidos:
            resumen += f" Se van a restablecer los circuitos: {', '.join(grupos_restablecidos)}."
        await client.send_message(GRUPO_ID, resumen)
    else:
        # Si no se detectan los circuitos de interés, se reenvía el mensaje completo
        if any(code in mensaje for code in ["121", "117", "113", "112"]):
            await client.send_message(GRUPO_ID, mensaje)


async def main():
    print("Inicializando base de datos...")
    await init_db()
    print("Bot en funcionamiento...")
    # Opcional: enviar mensaje de inicio
    # await client.send_message(GRUPO_ID, "✅ Bot iniciado correctamente")
    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(main())
