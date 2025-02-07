# Spanish (Español)

## Date and Time

- "qué hora es?"
- "qué día es?"

## Weather and Temperature

- "qué tiempo hace?"
    - Requires a [weather][] entity to be configured
- "qué tiempo hace en New York?"
    - Requires a [weather][] entity named "New York"
- "cuál es la temperatura?"
    - Requires a [climate][] entity to be configured
- "cuál es la temperatura del EcoBee?"
    - Requires a [climate][] entity named "EcoBee"
    
## Lights

- "enciende/apaga las luces"
    - Requires voice satellite to be in an [area][]
- "enciende/apaga la Lámpara"
    - Requires a [light][] entity named "Lámpara"
- "enciende/apaga las luces de la Oficina"
    - Requires an [area][] named "Oficina"
- "enciende/apaga las luces del Primer Piso"
    - Requires a [floor][] named "Primer Piso"
- "ajusta el color de las luces de la Cocina a verde"
    - Requires an [area][] named "Cocina" with at least one [light][] entity in it that supports setting color
- "ajusta el brillo de la Lámpara al 50 por ciento"
    - Requires a [light][] entity named "Lámpara" that supports setting brightness
    - Brightness from 10-100 by 10s

## Sensors

- "cuál es la Humedad Exterior?"
    - Requires a [sensor][] entity named "Humedad Exterior"

## Doors and Windows

- "abre/cierra la Puerta del Garaje"
    - Requires a [cover][] entity named "Puerta del Garaje"
- "está la Puerta del Garaje abierta/cerrada?"
    - Requires a [cover][] entity named "Puerta del Garaje"
    
## Locks

- "cierra con llave la Puerta Principal"
    - Requires a [lock][] entity named "Puerta Principal"
- "está cerrada con llave la Puerta Principal?"
    - Requires a [lock][] entity named "front door"

## Media

- "pausa"
    - Requires a [media player][] entity that is playing
- "continúa"
    - Requires a [media player][] entity that is paused
- "siguiente canción"
    - Requires a [media player][] entity to that is playing and supports next track

## Timers

- "inicia un temporizador de 5 minutos"
    - minutes from 1-10, 15, 20, 30, 40, 45, 50-100 by 10s
- "inicia un temporizador de 30 segundos"
    - seconds from 10-100 by 5s
- "inicia un temporizador de 3 horas y 10 minutos"
    - hours from 1-24
- "pausa/cancela el temporizador"
- "cancela el temporizador"
- "cancela todos los temporizadores"
- "estado de temporizador"

## Miscellaneous

- "no importa"

<!-- Links -->
[area]: https://www.home-assistant.io/docs/organizing/#area
[climate]: https://www.home-assistant.io/integrations/climate/
[cover]: https://www.home-assistant.io/integrations/cover/
[floor]: https://www.home-assistant.io/docs/organizing/#floor
[light]: https://www.home-assistant.io/integrations/light/
[lock]: https://www.home-assistant.io/integrations/lock/
[media player]: https://www.home-assistant.io/integrations/media_player/
[sensor]: https://www.home-assistant.io/integrations/sensor/
[weather]: https://www.home-assistant.io/integrations/weather/
