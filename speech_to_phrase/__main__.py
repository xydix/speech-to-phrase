"""Wyoming server."""

import argparse
import asyncio
import logging
from functools import partial
from pathlib import Path
from typing import Dict

from wyoming.server import AsyncServer

from .const import Settings
from .event_handler import SpeechToPhraseEventHandler
from .hass_api import HomeAssistantInfo, get_hass_info
from .models import DEFAULT_MODEL, Model, get_models_for_languages
from .train import train

_LOGGER = logging.getLogger()


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default="stdio://", help="unix:// or tcp://")
    parser.add_argument(
        "--train-dir", required=True, help="Directory to write trained model files"
    )
    parser.add_argument(
        "--tools-dir", required=True, help="Directory with kaldi, openfst, etc."
    )
    parser.add_argument(
        "--models-dir", required=True, help="Directory with speech models"
    )
    # Home Assistant
    parser.add_argument(
        "--hass-token", required=True, help="Long-lived access token for Home Assistant"
    )
    parser.add_argument(
        "--hass-websocket-uri",
        default="ws://homeassistant.local:8123/api/websocket",
        help="URI of Home Assistant websocket API",
    )
    parser.add_argument(
        "--retrain-on-connect",
        action="store_true",
        help="Automatically retrain on every client connection",
    )
    # Audio
    parser.add_argument("--volume-multiplier", type=float, default=1.0)
    #
    parser.add_argument("--debug", action="store_true", help="Log DEBUG messages")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    _LOGGER.debug(args)

    settings = Settings(
        models_dir=Path(args.models_dir),
        train_dir=Path(args.train_dir),
        tools_dir=Path(args.tools_dir),
        hass_token=args.hass_token,
        hass_websocket_uri=args.hass_websocket_uri,
        retrain_on_connect=args.retrain_on_connect,
    )

    # Train
    _LOGGER.info("Training started")

    _LOGGER.debug(
        "Getting exposed things from Home Assistant (%s)", settings.hass_websocket_uri
    )
    hass_info = await get_hass_info(
        token=settings.hass_token, uri=settings.hass_websocket_uri
    )
    _LOGGER.debug("HA system language: %s", hass_info.system_language)
    if hass_info.pipeline_languages:
        _LOGGER.debug("HA pipeline language(s): %s", hass_info.pipeline_languages)

    settings.default_language = hass_info.system_language
    things = hass_info.things
    _LOGGER.debug(
        "Got %s entities, %s area(s), %s floor(s), %s trigger sentence(s)",
        len(things.entities),
        len(things.areas),
        len(things.floors),
        len(things.trigger_sentences),
    )

    languages_to_train = list(hass_info.pipeline_languages) + [
        hass_info.system_language
    ]
    models_to_train = get_models_for_languages(languages_to_train)
    if not models_to_train:
        # Fall back to English model
        models_to_train = [DEFAULT_MODEL]

    model_train_tasks: Dict[str, asyncio.Task] = {
        model.id: asyncio.create_task(_train_model(model, settings, hass_info))
        for model in models_to_train
    }

    _LOGGER.info("Training started for models: %s", list(model_train_tasks.keys()))

    # Run server
    wyoming_server = AsyncServer.from_uri(args.uri)

    _LOGGER.info("Ready")

    try:
        await wyoming_server.run(
            partial(
                SpeechToPhraseEventHandler,
                settings,
                hass_info,
                model_train_tasks,
                args.volume_multiplier,
            )
        )
    except KeyboardInterrupt:
        pass


async def _train_model(
    model: Model, settings: Settings, hass_info: HomeAssistantInfo
) -> None:
    try:
        await train(model, settings, hass_info.things)
    except Exception:
        _LOGGER.exception("Unexpected error while training %s", model.id)
        raise


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
