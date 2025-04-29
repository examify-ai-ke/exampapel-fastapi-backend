# https://github.com/Longdh57/fastapi-minio

import os
from app.utils.uuid6 import uuid7
from datetime import timedelta
from minio import Minio
from pydantic import BaseModel
import os
import boto3
# from app.utils.uuid6 import uuid7
# from datetime import timedelta
# from pydantic import BaseModel
from botocore.client import Config

# minio_url = "http://127.0.0.1:9000"  # The Minio server URL
# access_key = os.getenv("MINIO_ACCESS_KEY")  # Your access key
# secret_key = os.getenv("MINIO_SECRET_KEY")
# bucket_name = os.getenv("MINIO_BUCKET")  # The bucket to work with

class IMinioResponse(BaseModel):
    bucket_name: str
    file_name: str
    url: str


class MinioClient:

    def __init__(
        self,
        minio_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        secure:bool=False,
    ):
        self.minio_url = minio_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.secure=secure
        self.client = Minio(
            self.minio_url,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False,
        )
        self.make_bucket()

    def make_bucket(self) -> str:
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
        return self.bucket_name

    def presigned_get_object(self, bucket_name, object_name):
        # Request URL expired after 7 days
        url = self.client.presigned_get_object(
            bucket_name=bucket_name, object_name=object_name, expires=timedelta(days=7)
        )
        return url

    def check_file_name_exists(self, bucket_name, file_name):
        try:
            self.client.stat_object(bucket_name=bucket_name, object_name=file_name)
            return True
        except Exception as e:
            print(f"[x] Exception: {e}")
            return False

    def put_object(self, file_data, file_name, content_type):
        try:
            object_name = f"{uuid7()}{file_name}"
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_data,
                content_type=content_type,
                length=-1,
                part_size=10 * 1024 * 1024,
            )
            url = self.presigned_get_object(
                bucket_name=self.bucket_name, object_name=object_name
            )
            data_file = IMinioResponse(
                bucket_name=self.bucket_name, file_name=object_name, url=url
            )
            return data_file
        except Exception as e:
            raise e


class S3Client:

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str,
        bucket_name: str,
    ):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.bucket_name = bucket_name
        self.client = boto3.client(
            "s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
            config=Config(signature_version="s3v4"),
        )
        self.resource = boto3.resource(
            "s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
        )
        self.make_bucket()

    def make_bucket(self) -> str:
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except:
            # Bucket doesn't exist, create it
            if self.region_name == "us-east-1":
                self.client.create_bucket(Bucket=self.bucket_name)
            else:
                self.client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": self.region_name},
                )
        return self.bucket_name

    def presigned_get_object(self, bucket_name, object_name):
        # Request URL expired after 7 days
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=7 * 24 * 3600,  # 7 days in seconds
        )
        # print("presigned_get_object...", url)
        return url

    def check_file_name_exists(self, bucket_name, file_name):
        try:
            self.client.head_object(Bucket=bucket_name, Key=file_name)
            return True
        except Exception as e:
            print(f"[x] Exception: {e}")
            return False

    def put_object(self, file_data, file_name, content_type):
        try:
            object_name = f"{uuid7()}{file_name}"
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=file_data,
                ContentType=content_type,
            )
            url = self.presigned_get_object(
                bucket_name=self.bucket_name, object_name=object_name
            )
            data_file = IMinioResponse(
                bucket_name=self.bucket_name, file_name=object_name, url=url
            )
            print("pry object data_file:", data_file)
            return data_file
        except Exception as e:
            raise e
