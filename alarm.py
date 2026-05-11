from datetime import datetime
import time

print("Alarmanlage gestartet...")

while True:
    zeit = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    meldung = "System läuft: " + zeit

    print(meldung)

    with open("alarm_log.txt", "a") as datei:
        datei.write(meldung + "\n")

    time.sleep(5)
