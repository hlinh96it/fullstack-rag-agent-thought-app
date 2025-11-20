from boto3 import client
from botocore.exceptions import ClientError

from src.config import Settings

import logging
logger = logging.getLogger(__name__)


class AWSClient:
    def __init__(self, settings: Settings):
        self.settings = settings.aws
        self.s3_client = client(
            's3', aws_access_key_id=self.settings.access_key,
            aws_secret_access_key=self.settings.secret_key
        )
        self.bucket_name = self.settings.bucket_name
        self.region = self.settings.region
        self._check_health()
        
    def _check_health(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f'👌  S3 client initialized successfully')
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f'Bucket {self.bucket_name} does not exist')
            elif error_code == '403':
                logger.error(f'Access denied for bucket {self.bucket_name}')
            else:
                logger.error(f'Error while checking bucket: {e}')

        