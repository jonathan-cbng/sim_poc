#!/usr/bin/env python
"""
Main entry point for the mode simulator application.

See ruff configuration in pyproject.toml for exact rules: pre-commit checks and CI/CD pipelines will enforce them.
"""
#######################################################################################################################
# Imports
#######################################################################################################################

import uvicorn

from src.config import settings
from src.controller.app import get_app

#######################################################################################################################
# Globals
#######################################################################################################################

#######################################################################################################################
# Body
#######################################################################################################################


def entry_point() -> None:
    """Starts the FastAPI application using Uvicorn.

    The controller is a single-worker application that spawns tasks for each AP/RT but stores state centrally in
    memory, so multiple workers would not work. This should be OK, as all the real work is done in the
    worker subprocesses: the controller should not be a bottleneck.
    """

    uvicorn.run(
        get_app(),
        port=settings.APP_PORT,
        host=settings.APP_HOST,
        workers=1,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    entry_point()

#######################################################################################################################
# End of file
#######################################################################################################################
