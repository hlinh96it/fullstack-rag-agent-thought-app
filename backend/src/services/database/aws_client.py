from boto3 import client

from src.config import Settings

class AWSClient:
    def __init__(self, settings: Settings):
        self.settings = settings.aws
        self.s3_client = client(
            's3', aws_access_key_id=self.settings.access_key,
            aws_secret_access_key=self.settings.secret_key
        )
        self.bucket_name = self.settings.bucket_name
        self.region = self.settings.region

        