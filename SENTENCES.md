# Sentences

Available voice commands by category and language code.

* `en` - English

**NOTE:**  Entities must first be [exposed][] in Home Assistant.

<!----------------------------------------------------------------------------->

## Cancel

Cancels the current command and does nothing:

| Language | Command   |
|----------|-----------|
| `en`     | nevermind |

<!----------------------------------------------------------------------------->

## Devices

Works with these [entity domains][entities]:

* [light][light]
* [switch][switch]
* [fan][fan]
* [media_player][media_player]
* [input_boolean][input_boolean]

| Language | Command               |
|----------|-----------------------|
| `en`     | turn on/off My Device |

<!----------------------------------------------------------------------------->

## Date and Time

| Language | Command                                    |
|----------|--------------------------------------------|
| `en`     | - what time is it? <br> - what's the date? |

<!----------------------------------------------------------------------------->

## Lights

Requires at least one [light][] entity in the same [area][] as the voice satellite:

| Language | Command                |
|----------|------------------------|
| `en`     | turn on/off the lights |

Requires at least one [light][] entity in an [area][] with the specific name or [alias][aliases]:

| Language | Command                           |
|----------|-----------------------------------|
| `en`     | turn on/off lights in the Kitchen |

### Brightness

Requires at least one [light][] entity that supports setting brightness in the same [area][] as the voice satellite:

| Language | Command                          |
|----------|----------------------------------|
| `en`     | set the brightness to 50 percent |

Requires at least one [light][] entity that supports setting brightness in an [area][] with the specific name or [alias][aliases]:

| Language | Command                              |
|----------|--------------------------------------|
| `en`     | set Kitchen brightness to 50 percent |

Requires a [light][] entity that supports setting brightness with the specific name or [alias][alises]:

| Language | Command                                |
|----------|----------------------------------------|
| `en`     | set Bed Light brightness to 50 percent |

### Color

Requires at least one [light][] entity that supports setting color in the same [area][] as the voice satellite:

| Language | Command           |
|----------|-------------------|
| `en`     | set lights to red |

Requires at least one [light][] entity that supports setting color in an [area][] with the specific name or [alias][aliases]:

| Language | Command                   |
|----------|---------------------------|
| `en`     | set Kitchen lights to red |

Requires a [light][] entity that supports setting color with the specific name or [alias][aliases]:

| Language | Command              |
|----------|----------------------|
| `en`     | set Bed Light to red |

<!----------------------------------------------------------------------------->

## Weather

Requires a [weather][] entity to be configured:

| Language | Command             |
|----------|---------------------|
| `en`     | what's the weather? |

Requires a [weather][] entity with the specific name or [alias][alises]:

| Language | Command                         |
|----------|---------------------------------|
| `en`     | what's the weather in New York? |

<!----------------------------------------------------------------------------->

## Temperature

Requires a [climate][] entity to be configured:

| Language | Command                 |
|----------|-------------------------|
| `en`     | what's the temperature? |


Requires a [climate][] entity with the specific name or [alias][alises]:

| Language | Command                               |
|----------|---------------------------------------|
| `en`     | what's the temperature of the EcoBee? |


<!----------------------------------------------------------------------------->

## Doors and Windows

Requires a [cover][] entity with the specific name or [alias][aliases]:

| Language | Command                                                               |
|----------|-----------------------------------------------------------------------|
| `en`     | - open/close the Sliding Door <br> - is the Sliding Door open/closed? |

<!----------------------------------------------------------------------------->

## Locks

Requires a [lock][] entity with the specific name or [alias][aliases]:

| Language | Command                                                            |
|----------|--------------------------------------------------------------------|
| `en`     | - lock/unlock the Deadbolt <br> - is the Deadbolt locked/unlocked? |

<!----------------------------------------------------------------------------->

## Sensors

Requires a [sensor][] entity with the specific name or [alias][aliases]:

| Language | Command                                |
|----------|----------------------------------------|
| `en`     | what is the value of Outdoor Humidity? |

<!----------------------------------------------------------------------------->

## Media

Requires a [media player][media_player] entity in the same [area][] as the voice satellite:

| Language | Command           |
|----------|-------------------|
| `en`     | pause/resume/next |

The media player must be in the appropriate state and support the command.

Requires a [media player][media_player] entity with the specific name or [alias][aliases]:

| Language | Command                             |
|----------|-------------------------------------|
| `en`     | - pause/resume TV <br> - next on TV |

The media player must be in the appropriate state and support the command.

<!----------------------------------------------------------------------------->

## Timers

Supported durations:

* 10-100 seconds in steps of 5
* 2-20 and 45 minutes
* 20-100 minutes in steps of 10
* 2-24 hours


| Language | Command                                                                                     |
|----------|---------------------------------------------------------------------------------------------|
| `en`     | - set a timer for 30 seconds <br> - set a timer for 5 minutes <br> - set a timer for 1 hour |

Minutes and seconds may be combined as well as hours and minutes:

| Language | Command                                                                                |
|----------|----------------------------------------------------------------------------------------|
| `en`     | - set a timer for 5 minutes and 30 seconds <br> - set a timer for 1 hour and 5 minutes |

Requires a timer to be set:

| Language | Command                                                                  |
|----------|--------------------------------------------------------------------------|
| `en`     | - pause/resume/cancel timer <br> - cancel all timers <br> - timer status |

<!----------------------------------------------------------------------------->

## Scenes and Scripts

Requires a [scene][] with the specific name or [alias][aliases]:

| Language | Command               |
|----------|-----------------------|
| `en`     | run party time script |

Requires a [script][] with the specific name or [alias][aliases]:

| Language | Command                      |
|----------|------------------------------|
| `en`     | activate mood lighting scene |

<!----------------------------------------------------------------------------->

<!-- Links -->
[aliases]: https://www.home-assistant.io/voice_control/aliases/
[area]: https://www.home-assistant.io/docs/organizing/#area
[climate]: https://www.home-assistant.io/integrations/climate/
[cover]: https://www.home-assistant.io/integrations/cover/
[entities]: https://www.home-assistant.io/docs/configuration/entities_domains/
[exposed]: https://www.home-assistant.io/voice_control/voice_remote_expose_devices/
[fan]: https://www.home-assistant.io/integrations/fan/
[input_boolean]: https://www.home-assistant.io/integrations/input_boolean/
[light]: https://www.home-assistant.io/integrations/light/
[lock]: https://www.home-assistant.io/integrations/lock/
[media_player]: https://www.home-assistant.io/integrations/media_player/
[scene]: https://www.home-assistant.io/integrations/scene/
[script]: https://www.home-assistant.io/integrations/script/
[sensor]: https://www.home-assistant.io/integrations/sensor/
[switch]: https://www.home-assistant.io/integrations/switch/
[weather]: https://www.home-assistant.io/integrations/weather/
