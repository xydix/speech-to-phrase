# Deutsch (German)

## Date and Time

- "wie spät ist es?"
- "welches datum ist heute?"

## Weather and Temperature

- "wie ist das Wetter?"
    - Requires a [weather][] entity to be configured
- "wie ist das Wetter in New York?"
    - Requires a [weather][] entity named "New York"
- "wie hoch ist die Temperatur?"
    - Requires a [climate][] entity to be configured
- "Wie hoch ist die Temperatur des EcoBee?"
    - Requires a [climate][] entity named "EcoBee"
    
## Lights

- "schalte das Licht an/aus"
    - Requires voice satellite to be in an [area][]
- "schalte die Lampe an/aus"
    - Requires a [light][] entity named "Lampe"
- "schalte das Licht im Büro an/aus"
    - Requires an [area][] named "Büro"
- "schalte die Lichter im ersten Stock an/aus"
    - Requires a [floor][] named "ersten Stock"
- "setze die Farbe der Lichter in der Küchen auf grün"
    - Requires an [area][] named "Küchen" with at least one [light][] entity in it that supports setting color
- "stelle die Helligkeit von der Lampe auf 50 Prozent"
    - Requires a [light][] entity named "Lampe" that supports setting brightness
    - Brightness from 10-100 by 10s

## Sensors

- "wie ist die Außenluftfeuchtigkeit?"
    - Requires a [sensor][] entity named "Außenluftfeuchtigkeit"

## Doors and Windows

- "öffne/schließ das Garagentor"
    - Requires a [cover][] entity named "Garagentor"
- "öffne/schließ alle Vorhänge im ersten Stock"
    - Requires a [floor][] named "ersten Stock" with at least one [cover][] entity whose [device class][cover device class] is `curtain`
    
## Locks

- "schließ die Vordertür ab/auf"
    - Requires a [lock][] entity named "Vordertür"
- "ist die Vordertür abgeschlossen"
    - Requires a [lock][] entity named "Vordertür"

## Media

- "pause"
    - Requires a [media player][] entity that is playing
- "fortsetzen"
    - Requires a [media player][] entity that is paused
- "nächsten Song"
    - Requires a [media player][] entity to that is playing and supports next track

## Timers

- "starte einen Timer für 5 Minuten"
    - minutes from 1-10, 15, 20, 30, 40, 45, 50-100 by 10s
- "starte einen Timer für 30 Sekunden"
    - seconds from 10-100 by 5s
- "starte einen Timer für 3 Stunden und 10 Minuten"
    - hours from 1-24
- "pausiere Timer",
- "setze den Timer fort"
- "stoppe den Timer"
- "beende alle Timer"
- "Timer Status"

## Miscellaneous

- "vergiss es"

<!-- Links -->
[area]: https://www.home-assistant.io/docs/organizing/#area
[climate]: https://www.home-assistant.io/integrations/climate/
[cover]: https://www.home-assistant.io/integrations/cover/
[cover device class]: https://www.home-assistant.io/integrations/cover/#device-class
[floor]: https://www.home-assistant.io/docs/organizing/#floor
[light]: https://www.home-assistant.io/integrations/light/
[lock]: https://www.home-assistant.io/integrations/lock/
[media player]: https://www.home-assistant.io/integrations/media_player/
[sensor]: https://www.home-assistant.io/integrations/sensor/
[weather]: https://www.home-assistant.io/integrations/weather/
