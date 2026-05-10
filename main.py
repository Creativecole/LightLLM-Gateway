"""Application entrypoint."""

import uvicorn

from gateway.app import create_app
from gateway.config import load_config

app = create_app()


if __name__ == "__main__":
    config = load_config()
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
    )
