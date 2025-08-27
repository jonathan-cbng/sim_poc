import logging

import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

if __name__ == "__main__":
    uvicorn.run("src.app:app", port=8000, workers=1)
    print("Done")
