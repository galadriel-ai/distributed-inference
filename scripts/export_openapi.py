import json

import settings


def main():
    settings.ENVIRONMENT = "production"
    settings.API_BASE_URL = "https://api.galadriel.com"

    import app

    docs = app.app.openapi()
    with open("scripts/openapi.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(docs, indent=2))


if __name__ == "__main__":
    main()
