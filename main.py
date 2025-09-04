import uvicorn

from src.app import get_app
from src.config import settings

if __name__ == "__main__":
    # The controller is a single-worker application - it spawns tasks for each AP/RT but stores state centrally in
    # memory, so multiple workers would not work. This should be OK, as the controller should not be a bottleneck.
    uvicorn.run(
        get_app(),
        port=settings.APP_PORT,
        host=settings.APP_HOST,
        workers=1,
        log_level=settings.LOG_LEVEL.lower(),
    )
    print("Done")
