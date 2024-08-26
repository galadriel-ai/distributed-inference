import uvicorn

import settings

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=settings.API_PORT,
        reload=True,
        timeout_keep_alive=120,
    )
