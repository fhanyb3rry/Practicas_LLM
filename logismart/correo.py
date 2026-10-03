import os
import smtplib
from email.message import EmailMessage


def armar_correo(correo, clasificacion, entidades):
    prioridad = str(clasificacion.get("prioridad", "")).upper()
    asunto = "[" + prioridad + "] " + str(clasificacion.get("categoria")) + " - " + str(correo.get("asunto"))

    cuerpo = "Incidente reportado por: " + str(correo.get("remitente")) + "\n"
    cuerpo += "Categoría: " + str(clasificacion.get("categoria")) + "\n"
    cuerpo += "Prioridad: " + str(clasificacion.get("prioridad")) + "\n"
    if clasificacion.get("requiere_revision_humana"):
        cuerpo += "REQUIERE REVISIÓN HUMANA\n"

    for campo in entidades:
        if entidades[campo] is not None:
            cuerpo += campo + ": " + str(entidades[campo]) + "\n"

    cuerpo += "\nMensaje original:\n" + str(correo.get("cuerpo"))
    return asunto, cuerpo


def enviar(remitente, destinatario, asunto, cuerpo, simulacion=True):
    # en simulación no se conecta a nada, solo avisa que lo habría enviado
    if simulacion:
        return {"enviado": True, "modo": "simulacion", "error": None}

    mensaje = EmailMessage()
    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)

    try:
        host = os.environ["SMTP_HOST"]
        puerto = int(os.environ.get("SMTP_PORT", "587"))
        usuario = os.environ["SMTP_USER"]
        clave = os.environ["SMTP_PASSWORD"]

        with smtplib.SMTP(host, puerto, timeout=15) as servidor:
            servidor.starttls()
            servidor.login(usuario, clave)
            servidor.send_message(mensaje)
        return {"enviado": True, "modo": "smtp", "error": None}
    except KeyError:
        return {"enviado": False, "modo": "smtp",
                "error": "Faltan SMTP_HOST, SMTP_USER y SMTP_PASSWORD en el archivo .env"}
    except (OSError, smtplib.SMTPException):
        return {"enviado": False, "modo": "smtp", "error": "No se pudo enviar el correo, revisa la conexión."}
