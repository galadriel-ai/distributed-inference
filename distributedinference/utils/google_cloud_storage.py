import asyncio
import base64
from google.cloud import storage
import settings


# pylint: disable=too-few-public-methods
class GoogleCloudStorage:
    def __init__(self):
        if settings.is_production():
            self.client = storage.Client()
        else:
            self.client = None

    async def decode_b64_and_upload_to_gcs(
        self, request_id: str, image_b64: str
    ) -> str:
        if not self.client:
            # TODO probably save it locally and return the path?
            return image_b64
        image_bytes = base64.b64decode(image_b64)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._upload_to_gcs, request_id, image_bytes
        )

    def _upload_to_gcs(self, request_id: str, image_bytes: bytes) -> str:
        bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(request_id)
        blob.upload_from_string(image_bytes, content_type="image/png")
        blob.make_public()
        return blob.public_url
