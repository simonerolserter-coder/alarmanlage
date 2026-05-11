from datetime import datetime
import subprocess
import time
import os
import json
import urllib.request
import urllib.parse
import threading
from gpiozero import DigitalInputDevice

# -------------------------------
# Alarmanlage mit echtem PIR-Sensor
# -------------------------------

alarm_aktiv = False
alarm_ausgeloest = False
bewegung_bereits_gemeldet = False
programm_laeuft = True

ONEDRIVE_ZIEL = "onedrive_alarmanlage_simon:Alarmanlage"

# OUT vom Bewegungsmelder steckt auf GPIO17 = physischer Pin 11
PIR_GPIO = 17
pir = DigitalInputDevice(PIR_GPIO, pull_up=False)


def aktuelle_zeit():
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def heutige_logdatei():
    datum = datetime.now().strftime("%d.%m.%Y")
    return f"alarm_log_{datum}.txt"


def log_event(event):
    log_datei = heutige_logdatei()

    zeit = aktuelle_zeit()
    eintrag = f"{zeit} | {event}"

    print(eintrag)

    with open(log_datei, "a", encoding="utf-8") as datei:
        datei.write(eintrag + "\n")

    sync_to_onedrive(log_datei)


def sync_to_onedrive(log_datei):
    try:
        subprocess.run(
            ["rclone", "copy", log_datei, ONEDRIVE_ZIEL],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"{log_datei} wurde nach OneDrive hochgeladen.")
    except subprocess.CalledProcessError as fehler:
        print("OneDrive-Upload fehlgeschlagen:")
        print(fehler.stderr)


def telegram_senden(nachricht):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram konnte nicht gesendet werden: Token oder Chat-ID fehlt.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    daten = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": nachricht
    }).encode("utf-8")

    try:
        with urllib.request.urlopen(url, data=daten, timeout=10) as antwort:
            ergebnis = json.loads(antwort.read().decode("utf-8"))

        if ergebnis.get("ok"):
            pass
        else:
            print("Telegram-Fehler:")
            print(ergebnis)

    except Exception as fehler:
        print("Telegram-Versand fehlgeschlagen:")
        print(fehler)


def led_status_simulation():
    if alarm_aktiv and not alarm_ausgeloest:
        print("LED GRÜN: AUS")
        print("LED ROT: AN")
    elif not alarm_aktiv:
        print("LED GRÜN: AN")
        print("LED ROT: AUS")
    elif alarm_ausgeloest:
        print("LED ROT: BLINKT")


def buzzer_simulation():
    print("BUZZER: BEEP BEEP BEEP")


def alarm_aktivieren():
    global alarm_aktiv, alarm_ausgeloest, bewegung_bereits_gemeldet

    alarm_aktiv = True
    alarm_ausgeloest = False

    # Wichtig:
    # Falls der Sensor beim Aktivieren gerade noch HIGH ist,
    # wird nicht sofort eine Telegram-Nachricht gesendet.
    if pir.value == 1:
        bewegung_bereits_gemeldet = True
    else:
        bewegung_bereits_gemeldet = False

    log_event("Alarmanlage aktiviert")
    led_status_simulation()


def alarm_deaktivieren():
    global alarm_aktiv, alarm_ausgeloest, bewegung_bereits_gemeldet

    alarm_aktiv = False
    alarm_ausgeloest = False
    bewegung_bereits_gemeldet = False

    log_event("Alarmanlage deaktiviert")
    led_status_simulation()


def bewegung_erkannt():
    global alarm_ausgeloest

    if alarm_aktiv:
        alarm_ausgeloest = True

        benachrichtigung = "Der Alarm wurde ausgelöst."
        zeit = aktuelle_zeit()

        eintrag = f"{zeit} | {benachrichtigung}"

        print(eintrag)

        log_datei = heutige_logdatei()

        with open(log_datei, "a", encoding="utf-8") as datei:
            datei.write(eintrag + "\n")

        sync_to_onedrive(log_datei)

        led_status_simulation()
        buzzer_simulation()

        telegram_text = f"{zeit}\n{benachrichtigung}"
        telegram_senden(telegram_text)


def sensor_ueberwachen():
    global bewegung_bereits_gemeldet

    print("Bewegungsmelder wird überwacht...")

    while programm_laeuft:
        if alarm_aktiv:
            if pir.value == 1 and not bewegung_bereits_gemeldet:
                bewegung_erkannt()
                bewegung_bereits_gemeldet = True

            elif pir.value == 0 and bewegung_bereits_gemeldet:
                bewegung_bereits_gemeldet = False

        time.sleep(1)


def status_anzeigen():
    print()
    print("------ STATUS ------")
    print("Alarm aktiv:", alarm_aktiv)
    print("Alarm ausgelöst:", alarm_ausgeloest)
    print("Sensorwert:", "Bewegung" if pir.value == 1 else "Keine Bewegung")
    print("Aktuelle Logdatei:", heutige_logdatei())
    print("OneDrive-Ziel:", ONEDRIVE_ZIEL)
    print("--------------------")
    print()


def menue_anzeigen():
    print()
    print("===== ALARMANLAGE MIT BEWEGUNGSMELDER =====")

    if alarm_aktiv:
        print("[d] Alarmanlage deaktivieren")
    else:
        print("[a] Alarmanlage aktivieren")

    print("[s] Status anzeigen")
    print("[q] Programm beenden")
    print("===========================================")


def main():
    global programm_laeuft

    log_event("System gestartet")
    led_status_simulation()

    print("Sensor startet. Bitte 20 Sekunden nicht vor dem Sensor bewegen.")
    time.sleep(20)
    print("Sensor bereit.")

    sensor_thread = threading.Thread(target=sensor_ueberwachen, daemon=True)
    sensor_thread.start()

    while True:
        menue_anzeigen()
        eingabe = input("Befehl eingeben: ").lower()

        if eingabe == "a":
            alarm_aktivieren()

        elif eingabe == "d":
            alarm_deaktivieren()

        elif eingabe == "s":
            status_anzeigen()

        elif eingabe == "q":
            programm_laeuft = False
            log_event("System beendet")
            print("Programm wird beendet.")
            break

        else:
            print("Ungültige Eingabe. Bitte a, d, s oder q eingeben.")

        time.sleep(1)


main()
