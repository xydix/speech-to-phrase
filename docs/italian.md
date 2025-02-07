# Italian (Italiano)

## Date and Time

- "che ore sono?"
- "che giorno è oggi?"

## Weather and Temperature

- "che tempo fa?"
    - Requires a [weather][] entity to be configured
- "che tempo fa a New York?"
    - Requires a [weather][] entity named "New York"
- "qual è la temperatura?"
    - Requires a [climate][] entity to be configured
- "qual è la temperatura in Cucina?"
    - Requires an [area][] named "Cucina" with a [climate][] entity
    
## Lights

- "accendi/spegni le luci"
    - Requires voice satellite to be in an [area][]
- "accendi/spegni la Lampada"
    - Requires a [light][] entity named "standing light"
- "imposta le luci in Cucina su verde"
    - Requires an [area][] named "Cucina" with at least one [light][] entity in it that supports setting color
- "imposta la luminosità della Lampada al 50 percento"
    - Requires a [light][] entity named "Lampada" that supports setting brightness
    - Brightness from 10-100 by 10s

## Doors and Windows

- "chiudi la Porta del Garage"
    - Requires a [cover][] entity named "Porta del Garage"
- "la Porta del Garage è apertoa?"
    - Requires a [cover][] entity named "Porta del Garage"
    
## Media

- "pausa"
    - Requires a [media player][] entity that is playing
- "riprendi"
    - Requires a [media player][] entity that is paused
- "vai avanti"
    - Requires a [media player][] entity to that is playing and supports next track

## Timers

- "imposta un timer di 5 minuti"
    - minutes from 1-10, 15, 20, 30, 40, 45, 50-100 by 10s
- "imposta timer di 30 secondi"
    - seconds from 10-100 by 5s
- "imposta timer di 3 ore e 10 minuti"
    - hours from 1-24
- "metti in pausa il mio timer"
- "riprendi timer"
- "annulla il timer"
- "cancella tutti i miei timer"
- "stato timer"

## Miscellaneous

- "lascia stare"

<!-- Links -->
[area]: https://www.home-assistant.io/docs/organizing/#area
[climate]: https://www.home-assistant.io/integrations/climate/
[cover]: https://www.home-assistant.io/integrations/cover/
[floor]: https://www.home-assistant.io/docs/organizing/#floor
[light]: https://www.home-assistant.io/integrations/light/
[lock]: https://www.home-assistant.io/integrations/lock/
[media player]: https://www.home-assistant.io/integrations/media_player/
[weather]: https://www.home-assistant.io/integrations/weather/
