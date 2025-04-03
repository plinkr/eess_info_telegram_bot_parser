import os
import re

from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel

# Credenciales de la API de Telegram
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CANAL_ID = 1579333735  # ID numérico del canal "informateessp"
# CANAL_ID = 2436767198  # ID numérico del canal "plinkr_oss"
GRUPO_ID = int(os.getenv("GRUPO_ID"))  # ID del grupo destino

client = TelegramClient("bot_session", API_ID, API_HASH)


def extraer_info(mensaje: str):
    """
    Extrae la hora, los circuitos a afectar y a restablecer, y el tiempo aproximado de afectación.
    Se separa el mensaje en dos bloques (afectar y restablecer) y se busca la hora en el mensaje.
    Si no se encuentra hora, se asigna "Hora no encontrada".
    """
    # Buscar la hora en el mensaje (ej: "Para las 8:55 am")
    hora_match = re.search(r"Para las?\s*(\d{1,2}:\d{2}\s*(?:am|pm))", mensaje, re.IGNORECASE)
    hora = hora_match.group(1) if hora_match else "Hora no encontrada"

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

    # Extraer el texto del tiempo de afectación (aplica para el bloque de afectar)
    tiempo_match = re.search(r"Tiempo aproximado de afectación hasta\s*([^.\n]+)", mensaje, re.IGNORECASE)
    tiempo = tiempo_match.group(0) if tiempo_match else ""

    # Definir los circuitos de interés
    circuits_interes = ["121", "117", "113", "112"]
    afectados = set()
    restablecidos = set()

    # Buscar en el bloque de afectar
    for circuito in circuits_interes:
        if re.search(r"\b" + re.escape(circuito) + r"\b", affect_block):
            afectados.add(circuito)
    # Buscar en el bloque de restablecer
    for circuito in circuits_interes:
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


@client.on(events.NewMessage(chats=[PeerChannel(CANAL_ID)]))
async def handler(event):
    mensaje = event.raw_text
    # print(f"Mensaje recibido: {mensaje}")  # Para depuración

    hora, afectados, restablecidos, tiempo = extraer_info(mensaje)

    # Agrupar circuitos para cada bloque según la detección individual
    grupos_afectados = agrupar_circuitos(afectados)
    grupos_restablecidos = agrupar_circuitos(restablecidos)

    # Solo se envía resumen si se detecta alguno de los circuitos de interés
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
    print("Bot en funcionamiento...")
    # Opcional: enviar mensaje de inicio
    # await client.send_message(GRUPO_ID, "✅ Bot iniciado correctamente")
    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(main())
