from typing import Dict, Optional
import json
import asyncio
import boto3
from distributedinference import api_logger
from distributedinference.utils.timer import async_timer

logger = api_logger.get()


class AWSStorageRepository:
    def __init__(self, bucket_name: str):
        self.iam_client = boto3.client("iam")
        self.s3_client = boto3.client("s3")
        self.bucket_name = bucket_name

    @async_timer("aws_storage_repository.create_user_and_bucket_access", logger=logger)
    async def create_user_and_bucket_access(
        self, agent_id: str
    ) -> Optional[Dict[str, str]]:
        folder_name = agent_id
        loop = asyncio.get_event_loop()

        try:
            # Create the IAM user
            logger.info(f"Creating IAM user: {agent_id}")
            await loop.run_in_executor(
                None, lambda: self.iam_client.create_user(UserName=agent_id)
            )

            # Create access keys for the IAM user
            logger.info("Creating access keys for the user...")
            access_key_response = await loop.run_in_executor(
                None, lambda: self.iam_client.create_access_key(UserName=agent_id)
            )
            access_key = access_key_response["AccessKey"]["AccessKeyId"]
            secret_key = access_key_response["AccessKey"]["SecretAccessKey"]

            # Create the S3 folder
            folder_key = f"{folder_name}/"
            logger.info(f"Creating folder: {folder_key} in bucket {self.bucket_name}")
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name, Key=folder_key
                ),
            )

            # Attach an inline policy to the user to allow full access to the specific folder
            logger.info("Attaching folder policy to the user...")
            folder_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "s3:*",
                        "Resource": f"arn:aws:s3:::{self.bucket_name}/{folder_key}*",
                    }
                ],
            }
            policy_name = f"{agent_id}_policy"
            await loop.run_in_executor(
                None,
                lambda: self.iam_client.put_user_policy(
                    UserName=agent_id,
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(folder_policy),
                ),
            )

            return {"access_key": access_key, "secret_key": secret_key}

        except Exception as e:
            logger.error(f"Error creating user and bucket access: {e}")
            return None

    @async_timer("aws_storage_repository.cleanup_user_and_bucket_access", logger=logger)
    async def cleanup_user_and_bucket_access(self, agent_id: str) -> bool:
        folder_name = agent_id
        loop = asyncio.get_event_loop()

        try:
            # Detach and delete inline policies for the user
            logger.info(f"Deleting policies for user: {agent_id}")
            policies_response = await loop.run_in_executor(
                None, lambda: self.iam_client.list_user_policies(UserName=agent_id)
            )
            policies = policies_response["PolicyNames"]
            for policy_name in policies:
                await loop.run_in_executor(
                    None,
                    # pylint: disable=cell-var-from-loop
                    lambda: self.iam_client.delete_user_policy(
                        UserName=agent_id, PolicyName=policy_name
                    ),
                )

            # Delete access keys for the user
            logger.info(f"Deleting access keys for user: {agent_id}")
            access_keys_response = await loop.run_in_executor(
                None, lambda: self.iam_client.list_access_keys(UserName=agent_id)
            )
            access_keys = access_keys_response["AccessKeyMetadata"]
            for access_key in access_keys:
                await loop.run_in_executor(
                    None,
                    # pylint: disable=cell-var-from-loop
                    lambda: self.iam_client.delete_access_key(
                        UserName=agent_id, AccessKeyId=access_key["AccessKeyId"]
                    ),
                )

            # Delete the IAM user
            logger.info(f"Deleting IAM user: {agent_id}")
            await loop.run_in_executor(
                None, lambda: self.iam_client.delete_user(UserName=agent_id)
            )

            # Delete the S3 folder
            logger.info(f"Deleting folder: {folder_name} in bucket {self.bucket_name}")
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.delete_object(
                    Bucket=self.bucket_name, Key=f"{folder_name}/"
                ),
            )

            return True

        except Exception as e:
            logger.error(f"Error cleaning up user and bucket access: {e}")
            return False
