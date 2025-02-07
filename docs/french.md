# Français (French)

## Date and Time

- "quelle heure est-il?"
- "quel jour sommes-nous?"

## Weather and Temperature

- "quel temps fait-il?"
    - Requires a [weather][] entity to be configured
- "quel temps fait-il à New York?"
    - Requires a [weather][] entity named "New York"
- "combien fait-il?"
    - Requires a [climate][] entity to be configured
- "combien fait-il dans le Salon?"
    - Requires an [area][] named "Salon" with a [climate][] entity
    
## Lights

- "allume/éteins la lumière"
    - Requires voice satellite to be in an [area][]
- "allume/éteins la lampe"
    - Requires a [light][] entity named "lampe"
- "allume/éteins les lumières dans le Salon"
    - Requires an [area][] named "Salon"
- "allume/éteins toutes les lumières dans le Rez-de-chaussée"
    - Requires a [floor][] named "Rez-de-chaussée"
- "allume le Bureau en rouge"
    - Requires an [area][] named "Bureau" with at least one [light][] entity in it that supports setting color
- "allume le Rez-de-chaussée à 80 pourcent"
    - Requires a [light][] entity named "bed light" that supports setting brightness
    - Brightness from 10-100 by 10s

## Sensors

- "quel est l'humidité extérieure?"
    - Requires a [sensor][] entity named "humidité extérieurre"

## Doors and Windows

- "ouvre/ferme la porte du garage"
    - Requires a [cover][] entity named "porte du garage"
- "ouvre/ferme les rideaux du Rez-de-chaussée"
    - Requires an [area][] named "Rez-de-chaussée" with at least one [cover][] entity whose [device class][cover device class] is `curtain`
    
## Locks

- "déverrouille/verrouille la porte d'entrée"
    - Requires a [lock][] entity named "porte d'entrée"

## Media

- "pause"
    - Requires a [media player][] entity that is playing
- "lecture"
    - Requires a [media player][] entity that is paused
- "suivant"
    - Requires a [media player][] entity to that is playing and supports next track

## Timers

- "minuteur 5 minutes"
    - minutes from 1-10, 15, 20, 30, 40, 45, 50-100 by 10s
- "minuteur 30 secondes"
    - seconds from 10-100 by 5s
- "minuteur 3 heures et 10 minutes"
    - hours from 1-24
- "mets le minuteur en pause",
- "reprends le minuteur"
- "supprime le minuteur"
- "supprime tous les minuteurs"
- "combien de temps reste-t-il"

## Miscellaneous

- "annuler"

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
