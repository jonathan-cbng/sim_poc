import logging

import uvicorn

from src.app import get_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

if __name__ == "__main__":
    uvicorn.run(get_app(), port=8000, workers=1)
    print("Done")
