import json
import os
from typing import Optional
from borsh_construct import CStruct, U8
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Confirmed

# pylint: disable=import-error
from solders.system_program import ID as SYS_PROGRAM_ID
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.keypair import Keypair
from solders.signature import Signature
from solders.instruction import Instruction, AccountMeta
from solders.message import Message


from distributedinference import api_logger

logger = api_logger.get()

AUTHORITY_DATA_PDA_SEED = b"galadriel"
INSTRUCTION_DISCRIMINATORS = {
    "add_authority": [229, 9, 106, 73, 91, 213, 109, 183],
    "remove_authority": [242, 104, 208, 132, 190, 250, 74, 216],
    "add_proof": [107, 208, 160, 164, 154, 140, 136, 102],
    "initialize": [175, 175, 109, 31, 13, 152, 155, 237],
}


def _load_or_create_keypair(dir: str) -> Keypair:
    dir = os.path.expanduser(dir)
    keypair = _get_private_key(dir)
    if keypair is None:
        logger.info("No existing keypair found. Creating a new keypair...")
        keypair = Keypair()
        _save_private_key(keypair, dir)
    return keypair


def _get_private_key(dir: str) -> Optional[Keypair]:
    if os.path.exists(dir):
        with open(dir, "r", encoding="utf-8") as file:
            seed = json.load(file)
            return Keypair.from_bytes(seed)
    return None


def _save_private_key(keypair: Keypair, dir: str):
    private_key_json = json.dumps(keypair.to_bytes_array()).encode("utf-8")
    with open(dir, "wb") as file:
        file.write(private_key_json)


class AttestationProof:
    def __init__(
        self,
        hashed_data: bytes,
        signature: bytes,
        public_key: bytes,
        attestation: bytes,
    ):
        self.schema = CStruct(
            "hashed_data" / U8[32],
            "signature" / U8[64],
            "public_key" / U8[32],
            "attestation" / U8[32],
        )
        self.hashed_data = hashed_data
        self.signature = signature
        self.public_key = public_key
        self.attestation = attestation

    def serialize(self):
        return self.schema.build(
            {
                "hashed_data": self.hashed_data,
                "signature": self.signature,
                "public_key": self.public_key,
                "attestation": self.attestation,
            }
        )


class BlockchainProofRepository:

    def __init__(self, url: str, program_id: str, keypair_dir: str):
        self.client = AsyncClient(url)
        self.program_id = Pubkey.from_string(program_id)
        self.authority_data_pda = Pubkey.find_program_address(
            [bytes(AUTHORITY_DATA_PDA_SEED)], self.program_id
        )[0]
        self.keypair = _load_or_create_keypair(keypair_dir)

    async def is_connected(self):
        return await self.client.is_connected()

    async def close(self):
        await self.client.close()

    def get_keypair(self):
        return self.keypair

    async def call_instruction(
        self, signer: list[Keypair], data: bytes, accounts: list[AccountMeta]
    ):
        instruction = Instruction(self.program_id, data, accounts)
        message = Message([instruction])
        recent_blockhash_response = await self.client.get_latest_blockhash()
        recent_blockhash = recent_blockhash_response.value.blockhash
        transaction = Transaction(signer, message, recent_blockhash)
        return await self.client.send_transaction(
            transaction,
            opts=TxOpts(skip_confirmation=False, preflight_commitment=Confirmed),
        )

    async def get_recent_blockhash(self):
        await self.client.get_latest_blockhash()

    async def initialize_program(self):
        accounts = [
            AccountMeta(self.authority_data_pda, is_signer=False, is_writable=True),
            AccountMeta(self.keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=False),
        ]
        return await self.call_instruction(
            [self.keypair],
            bytes(INSTRUCTION_DISCRIMINATORS["initialize"]),
            accounts,
        )

    async def add_authority(self, authority: Pubkey):
        accounts = [
            AccountMeta(self.authority_data_pda, is_signer=False, is_writable=True),
            AccountMeta(self.keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(authority, is_signer=False, is_writable=False),
        ]
        return await self.call_instruction(
            [self.keypair],
            bytes(INSTRUCTION_DISCRIMINATORS["add_authority"]),
            accounts,
        )

    async def remove_authority(self, authority: Pubkey):
        accounts = [
            AccountMeta(self.authority_data_pda, is_signer=False, is_writable=True),
            AccountMeta(self.keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(authority, is_signer=False, is_writable=False),
        ]
        return await self.call_instruction(
            [self.keypair],
            bytes(INSTRUCTION_DISCRIMINATORS["remove_authority"]),
            accounts,
        )

    async def add_proof(self, proof: AttestationProof):
        if not isinstance(proof.hashed_data, bytes):
            proof.hashed_data = bytes(proof.hashed_data)
        proof_record_pda = Pubkey.find_program_address(
            [b"attestation", proof.hashed_data], self.program_id
        )[0]
        accounts = [
            AccountMeta(proof_record_pda, is_signer=False, is_writable=True),
            AccountMeta(self.authority_data_pda, is_signer=False, is_writable=True),
            AccountMeta(self.keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=False),
        ]
        data = bytes(INSTRUCTION_DISCRIMINATORS["add_proof"]) + proof.serialize()
        return await self.call_instruction([self.keypair], data, accounts)
