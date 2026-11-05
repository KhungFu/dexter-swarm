# 🖨 Abendberichte drucken

Der 👑 CEO-Kontrollgang schreibt bei Feierabend einen **Abendbericht**. Er landet in der 📬 Post und in den Aufgaben des CEO.
Dort steht der Knopf **🖨 Drucken**. Ein Klick fragt kurz nach („Abendbericht #12 jetzt auf „Buero“ drucken?“), erst nach
**OK** geht der Auftrag an den Drucker.

## Einrichten in drei Schritten

1. **Drucker im Betriebssystem verbinden** (einmalig, siehe unten für Pi und Windows).
2. In Hyperstead links **🖨 Drucker** öffnen, den Drucker wählen, mit **🧾 Testseite drucken** prüfen, ob es der richtige ist, dann **Speichern**.
3. Im selben Fenster **✅ Drucken erlauben**. Das ist ein Recht des CEO („Darf Abendberichte drucken“, auch im
   Einstellungen-Reiter des CEO). Mit **⛔ Drucken sperren** ist der Knopf wieder gesperrt.

Zum Ausprobieren ohne Drucker gibt es den **Testdrucker (Datei)**: Er druckt nicht, sondern legt den Ausdruck als
Textdatei in `workspace/.druck/` ab.

## Raspberry Pi (Linux, CUPS)

```bash
cd ~/paperclip-lite && ./install.sh --print          # installiert cups und cups-client
lpinfo --include-schemes dnssd,ipp -v                # zeigt Drucker im Netzwerk (wenn sie sich melden)
sudo lpadmin -p Buero -E -v ipp://192.168.1.50/ipp/print -m everywhere   # IP deines Druckers
lpstat -e                                            # muss "Buero" zeigen
```

Ein an einem Windows-Rechner **freigegebener** Drucker geht über Samba, aber **nie mit `-m raw`**: Dann schickt CUPS
reinen Text, den die meisten Drucker stillschweigend verwerfen (der Drucker wird gefunden, es kommt aber nichts heraus).
Richtig ist ein Treiber für dein Modell:

```bash
sudo apt install smbclient printer-driver-all
lpinfo -m | grep -i DEINMODELL                       # z. B. HP LaserJet -> Treibername merken
sudo lpadmin -p Buero -E -v smb://BENUTZER:PASSWORT@LAPTOP/DruckerName -m TREIBERNAME
```

Der Windows-Rechner muss dafür eingeschaltet sein. Moderne Netzwerkdrucker lieber direkt per `ipp://` ansprechen.

## Windows-Laptop

Einstellungen › Bluetooth und Geräte › **Drucker & Scanner** › Gerät hinzufügen. Ein freigegebener Drucker lässt sich
auch mit `\\SERVER\DruckerName` verbinden. Danach erscheint er unter 🖨 Drucker in Hyperstead (Hyperstead fragt
`Get-Printer` ab und druckt mit `Out-Printer`).

## Testseite kommt nicht heraus

Hyperstead prüft jetzt ein paar Sekunden nach dem Senden, ob der Auftrag wirklich läuft. Hängt er, steht die Ursache
im Fenster 🖨 Printer. **🩺 Check printer** zeigt jederzeit Zustand, wartende Aufträge und Treiber. Häufige Ursachen:

| Meldung | Ursache | Lösung |
|---|---|---|
| „CUPS has STOPPED this printer“ | CUPS hat den Drucker nach einem Fehler angehalten (meist nicht erreichbar). | Drucker einschalten, IP prüfen (`ping`), dann `sudo cupsenable Buero`. Details in `/var/log/cups/error_log`. |
| „set up WITHOUT a driver (raw)“ | Warteschlange mit `-m raw` angelegt, der Drucker versteht den Text nicht. | Neu anlegen mit `-m everywhere` (Netzwerkdrucker) oder Modelltreiber (siehe oben). |
| „Job … still waiting in the queue“ | Auftrag ist angenommen, aber der Drucker holt ihn nicht ab. | Ist der Drucker an und vom Pi erreichbar? `lpstat -o` zeigt die Warteschlange, `cancel -a Buero` leert sie. |
| Windows: „reports the printer as 'Offline'/'Paused'“ | Windows hält die Warteschlange an. | Einstellungen › Drucker & Scanner › Druckwarteschlange öffnen › „Drucker offline verwenden“ / „Drucken anhalten“ abwählen. |
| Windows: „A print job is stuck“ | Ein alter Auftrag blockiert alle folgenden. | In der Druckwarteschlange alle Aufträge abbrechen, Testseite erneut drucken. |
| Freigegebener Drucker (`\\SERVER\Drucker`) | Der Rechner, der ihn freigibt, ist aus. | Diesen Rechner einschalten. |
| „This is the test printer (file)“ | Gewählt ist der Testdrucker, er druckt nie auf Papier. | Den echten Drucker aus der Liste wählen. |

## Was passiert, wenn etwas fehlt

| Fehlt | Was Hyperstead macht |
|---|---|
| CUPS (`lp`, `lpstat`) auf dem Pi | Im Fenster 🖨 Drucker steht „CUPS fehlt“, nur der Testdrucker ist wählbar. |
| Kein Drucker gewählt | Der Knopf 🖨 Drucken meldet „Noch kein Drucker gewählt“ und öffnet das Drucker-Fenster. |
| Recht des CEO aus | Meldung „Drucken ist gesperrt“, es wird nichts gesendet. |
| Drucker aus oder nicht erreichbar | CUPS/Windows nimmt den Auftrag meist an und druckt, sobald der Drucker wieder da ist; meldet das System einen Fehler, steht er in der Meldung und im 📜 Verlauf (`print_failed`). |
| Abendbericht noch leer | Kein Druck-Knopf, bzw. Meldung „Der Abendbericht ist noch leer“. |
