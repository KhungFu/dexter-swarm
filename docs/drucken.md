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

**„Gefunden“ heißt noch nicht „eingerichtet“.** `lpstat -e` (und damit die Liste in Hyperstead) zeigt auch Drucker,
die sich nur im Netzwerk melden. CUPS kann auf ihnen oft nicht drucken, solange sie nicht als Warteschlange angelegt
sind: Die Testseite kommt dann nicht heraus. Hyperstead markiert sie als „(found on the network, not set up)“. Ein
Klick auf **🔧 Set up printer** legt sie einmalig an (`lpadmin -p NAME -E -v ADRESSE -m everywhere -o printer-is-shared=true`).
Darf der Hyperstead-Benutzer keine Drucker ändern (nicht in der Gruppe `lpadmin`), zeigt die Meldung den fertigen
`sudo lpadmin …`-Befehl. Kann der Drucker nicht treiberlos drucken (ältere Geräte), braucht er einen Modelltreiber (unten).

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

**Eigene Drucker des Laptops:** Hyperstead liest die Liste direkt aus der Windows-Druckwarteschlange (`winspool`,
wie das Druckmenü jedes Programms), ohne PowerShell. Alle lokal installierten und verbundenen Drucker erscheinen,
der Windows-Standarddrucker steht vorn und ist vorausgewählt. Nur wenn das scheitert, fragt Hyperstead PowerShell
(`Get-Printer`, dann `Win32_Printer`). Gedruckt wird mit `Out-Printer` (Zeitlimit `PCL_PRINT_WIN_TIMEOUT`, Std. 120 s,
weil PowerShell auf langsamen Laptops lange startet); fehlt PowerShell, druckt Notepad (`notepad /pt`).

Windows zeigt nur Drucker, die **in Windows** eingerichtet sind. Weitere Drucker trägst du als entfernte Drucker ein
(nächster Abschnitt) oder fügst sie in Windows hinzu:

**Drucker in Windows hinzufügen:** Einstellungen › Bluetooth und Geräte › **Drucker & Scanner** › Gerät hinzufügen
(installiert einen Windows-Treiber). Ein freigegebener Drucker lässt sich auch mit `\\SERVER\DruckerName` verbinden.
Danach erscheint er unter 🖨 Drucker (Hyperstead fragt `Get-Printer` ab, notfalls `Win32_Printer`, und druckt mit
`Out-Printer`). Stehen nur „Microsoft Print to PDF“, „OneNote“ oder „Fax“ in der Liste, ist noch kein echter Drucker
verbunden; das sagt Hyperstead dann auch. Kann Windows die Drucker gar nicht lesen, steht der Fehler im Fenster (meist
läuft der Dienst „Druckwarteschlange“/„Print Spooler“ nicht: `services.msc`).

## Entfernte Drucker (IP, Adresse, Cloud, E-Mail)

Unter 🖨 Printer bei **Remote printers** je Zeile eine Adresse eintragen, **Use** klicken. Die eigenen Drucker des
Rechners bleiben oben in der Liste, die entfernten stehen darunter. Gedruckt wird erst nach deiner Bestätigung.

| Eintrag | Beispiel | Was Hyperstead macht |
|---|---|---|
| IP oder Name eines Netzwerkdruckers | `192.168.0.223`, `EPSON3B79F0.local` | Spricht den Drucker direkt per IPP an (sucht `/ipp/print`). Schickt PDF, kann der Drucker das nicht, JPEG je Seite. Kein Treiber nötig. |
| Volle Drucker-Adresse (auch im Internet) | `ipp://drucker.example.com/ipp/print`, `ipps://…` | Wie oben, genau diese Adresse. `ipps://` = verschlüsselt (Zertifikat muss gültig sein). |
| Rechner, der Drucker freigibt (CUPS, z. B. ein Linux-Rechner) | `dexter.local` | Seine Drucker erscheinen als „Name @ dexter.local“. Dort einmal `sudo cupsctl --remote-any --share-printers`. |
| E-Mail-Adresse des Druckers | `abc123@print.epsonconnect.com` (Epson Connect), `…@hpeprint.com` (HP ePrint) | Schickt den Ausdruck als PDF-Anhang. Braucht SMTP in der `.env` (unten). Die Absenderadresse muss im Cloud-Dienst des Druckers erlaubt sein (Epson Connect: „Approved Senders List“). |

E-Mail-Versand in der `.env`:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587               # 465 = SSL, sonst STARTTLS (SMTP_STARTTLS=0 schaltet es ab)
SMTP_USER=ich@gmail.com
SMTP_PASSWORD=App-Passwort  # bei Gmail ein App-Passwort, nicht das normale Passwort
SMTP_FROM=ich@gmail.com     # optional, sonst SMTP_USER
```

Statt im Fenster gehen die Adressen auch als `PCL_REMOTE_PRINTERS=192.168.0.223,abc@print.epsonconnect.com` in die
`.env` (das alte `PCL_CUPS_SERVER` gilt weiter). 🩺 Check printer zeigt bei entfernten Druckern Zustand, Meldungen
(z. B. „out of paper“), unterstützte Formate und wartende Aufträge.

**Windows druckt jetzt so:** zuerst `Out-Printer`; scheitert das (z. B. „Das Handle ist ungültig“, wenn Hyperstead ohne
Konsolenfenster läuft), mit .NET `PrintDocument`, zuletzt mit Notepad.

## Testseite kommt nicht heraus

Hyperstead prüft jetzt ein paar Sekunden nach dem Senden, ob der Auftrag wirklich läuft. Hängt er, steht die Ursache
im Fenster 🖨 Printer. **🩺 Check printer** zeigt jederzeit Zustand, wartende Aufträge und Treiber. Häufige Ursachen:

| Meldung | Ursache | Lösung |
|---|---|---|
| „CUPS has STOPPED this printer“ | CUPS hat den Drucker nach einem Fehler angehalten (meist nicht erreichbar). | Drucker einschalten, IP prüfen (`ping`), dann `sudo cupsenable Buero`. Details in `/var/log/cups/error_log`. |
| „set up WITHOUT a driver (raw)“ | Warteschlange mit `-m raw` angelegt, der Drucker versteht den Text nicht. | Neu anlegen mit `-m everywhere` (Netzwerkdrucker) oder Modelltreiber (siehe oben). |
| „Job … still waiting in the queue“ | Auftrag ist angenommen, aber der Drucker holt ihn nicht ab. | Ist der Drucker an und erreichbar? `lpstat -o` zeigt die Warteschlange, `cancel -a Buero` leert sie. |
| Windows: „reports the printer as 'Offline'/'Paused'“ | Windows hält die Warteschlange an. | Einstellungen › Drucker & Scanner › Druckwarteschlange öffnen › „Drucker offline verwenden“ / „Drucken anhalten“ abwählen. |
| Windows: „A print job is stuck“ | Ein alter Auftrag blockiert alle folgenden. | In der Druckwarteschlange alle Aufträge abbrechen, Testseite erneut drucken. |
| Freigegebener Drucker (`\\SERVER\Drucker`) | Der Rechner, der ihn freigibt, ist aus. | Diesen Rechner einschalten. |
| „CUPS has only SEEN this printer on the network“ / „only found on the network“ | Pi: Der Drucker ist nur gefunden, nicht eingerichtet. | **🔧 Set up printer** klicken oder `sudo lpadmin -p NAME -E -v ADRESSE -m everywhere`. |
| „No destination host name supplied by cups-browsed“ / „set up automatically by cups-browsed“ | Linux: Der Drucker wurde von cups-browsed automatisch angelegt (`implicitclass://`), der Dienst liefert keine Adresse mehr. `cupsenable` hilft nicht. | Einmal fest einrichten: `sudo lpadmin -p Epson -E -v ipp://DRUCKER-IP/ipp/print -m everywhere`, dann „Epson“ wählen. Alter Eintrag: `sudo lpadmin -x 'ALTER_NAME'` (löscht auch seine wartenden Aufträge). |
| „Cannot reach ADRESSE“ | Entfernter Drucker aus, Adresse falsch oder nicht im selben Netz. | Drucker einschalten, IP statt Namen versuchen. Bei einem CUPS-Rechner dort `sudo cupsctl --remote-any --share-printers`. |
| „only accepts image/pwg-raster …“ | Der Drucker kann weder PDF noch JPEG noch Text. | Drucker in Windows mit Treiber hinzufügen oder über einen CUPS-Rechner drucken. |
| „E-mail to the printer failed“ / „needs SMTP_HOST“ | SMTP fehlt oder ist falsch. | SMTP-Werte in der `.env` prüfen (oben). |
| „The printer is not shared“ | Drucker auf dem CUPS-Rechner nicht freigegeben. | Dort `sudo lpadmin -p NAME -o printer-is-shared=true`. |
| „This is the test printer (file)“ | Gewählt ist der Testdrucker, er druckt nie auf Papier. | Den echten Drucker aus der Liste wählen. |

## Was passiert, wenn etwas fehlt

| Fehlt | Was Hyperstead macht |
|---|---|
| Drucker in Windows | Hinweis im Fenster, dass Windows keinen echten Drucker hat. Entfernte Drucker per Adresse gehen trotzdem. |
| Entfernter Drucker aus oder nicht erreichbar | Er steht als „not reachable“ in der Liste, Meldung „Cannot reach …“; die eigenen Drucker und der Testdrucker bleiben wählbar. |
| SMTP in der `.env` (E-Mail-Drucker) | Meldung „needs SMTP_HOST …“, es wird nichts gesendet. |
| CUPS (`lp`, `lpstat`) auf dem Pi | Im Fenster 🖨 Drucker steht „CUPS fehlt“, nur der Testdrucker ist wählbar. |
| Kein Drucker gewählt | Der Knopf 🖨 Drucken meldet „Noch kein Drucker gewählt“ und öffnet das Drucker-Fenster. |
| Recht des CEO aus | Meldung „Drucken ist gesperrt“, es wird nichts gesendet. |
| Drucker aus oder nicht erreichbar | CUPS/Windows nimmt den Auftrag meist an und druckt, sobald der Drucker wieder da ist; meldet das System einen Fehler, steht er in der Meldung und im 📜 Verlauf (`print_failed`). |
| Abendbericht noch leer | Kein Druck-Knopf, bzw. Meldung „Der Abendbericht ist noch leer“. |
