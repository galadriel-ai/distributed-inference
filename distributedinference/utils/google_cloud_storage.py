import asyncio
import base64
from datetime import timedelta
from google.cloud import storage
from distributedinference.api_logger import api_logger
import settings

logger = api_logger.get()

URL_EXPIRATION_MINUTES = 2 * 60


# pylint: disable=too-few-public-methods
class GoogleCloudStorage:
    def __init__(self):
        if settings.is_production():
            try:
                self.client = storage.Client()
            except Exception as e:
                logger.error(f"Error initializing Google Cloud Storage client: {e}")
                self.client = None
        else:
            self.client = None

    async def decode_b64_and_upload_to_gcs(
        self, request_id: str, idx: int, image_b64: str
    ) -> str:
        if not self.client:
            # TODO probably save it locally and return the path?
            return image_b64
        image_bytes = base64.b64decode(image_b64)
        blob_name = f"{request_id}_{idx}.png"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._upload_to_gcs, blob_name, image_bytes
        )

    def _upload_to_gcs(self, blob_name: str, image_bytes: bytes) -> str:
        bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(image_bytes, content_type="image/png")
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=URL_EXPIRATION_MINUTES),
            method="GET",
        )
        return url
