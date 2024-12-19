from typing import Optional

import argparse
import asyncio
import json
import os
import sys

# pylint: disable=import-error
from solders.keypair import Keypair
from solders.pubkey import Pubkey

script_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.join(script_dir, "distributedinference")
sys.path.append(api_dir)
# pylint: disable=C0413
from distributedinference.repository.blockchain_proof_repository import (
    BlockchainProofRepository,
)

KEYPAIR_DIR = "~/.config/solana/id.json"
SOLANA_RPC_URL = "https://api.devnet.solana.com"
SOLANA_PROGRAM_ID = "HCkvLKhWQ8TTRdoSry29epRZnAoEDhP9CjmDS8jLtY9"


async def main(
    arg_add: Optional[str], arg_remove: Optional[str], arg_transfer: Optional[str]
):
    # Create a ContractClient object
    keypair = None
    with open(os.path.expanduser(KEYPAIR_DIR), "r", encoding="utf-8") as file:
        seed = json.load(file)
        keypair = Keypair.from_bytes(seed)
    if not keypair:
        print("No key file found, exit...")
        return
    print(f"Loaded keypair: {keypair.pubkey()}")
    client = BlockchainProofRepository(SOLANA_RPC_URL, SOLANA_PROGRAM_ID, KEYPAIR_DIR)
    # Call the is_connected method of the client object
    is_connected = await client.is_connected()
    # Print the result
    if not is_connected:
        print("Failed to connect to Solana RPC")
        return

    if arg_add:
        # Call the add_authority method of the client object
        print(f"Adding authority: {arg_add}")
        response = await client.add_authority(Pubkey.from_string(arg_add))
        print(response)
    elif arg_remove:
        # Call the remove_authority method of the client object
        print(f"Removing authority: {arg_remove}")
        response = await client.remove_authority(Pubkey.from_string(arg_remove))
        print(response)
    elif arg_transfer:
        # Call the transfer method of the client object
        print(f"Transferring funds to: {arg_transfer}")
        # response = await client.transfer(Pubkey.from_string(arg_transfer), 1000000)
        # print(response)

    # Call the close method of the client object
    await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add or remove authority to/from Solana contract"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-a", "--add", help="Public key to add as authority")
    group.add_argument("-r", "--remove", help="Public key to remove as authority")
    group.add_argument("-t", "--transfer", help="Public key to transfer funds to")

    args = parser.parse_args()
    asyncio.run(main(args.add, args.remove, args.transfer))
