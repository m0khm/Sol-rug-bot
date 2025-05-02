#src/pump_client.py
import os
import json
from pathlib import Path
from solana.rpc.async_api import AsyncClient
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Confirmed
from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address
from anchorpy import Program, Provider, Wallet, Context


class PumpClient:
    # офиц. ID программы Pump.fun
    PROGRAM_ID = PublicKey("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
    # метаданные (Metaplex)
    MPL_TOKEN_METADATA = PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
    # сид-пфы
    METADATA_SEED = b"metadata"
    BONDING_SEED = b"bonding-curve"

    def __init__(self):
        rpc = os.getenv("SOLANA_RPC_ENDPOINT")
        keypair_path = Path(os.getenv("SOLANA_KEYPAIR_PATH"))
        secret = json.loads(keypair_path.read_text())
        self.keypair = Keypair.from_secret_key(bytes(secret))
        self.connection = AsyncClient(rpc, commitment=Confirmed)
        self.wallet = Wallet(self.keypair)
        self.provider = Provider(self.connection, self.wallet)
        # грузим IDL
        idl = json.loads(Path("src/pump_idl.json").read_text())
        self.program = Program(idl, self.PROGRAM_ID, self.provider)

    async def create_token(self, name: str, symbol: str, uri: str) -> dict:
        # новый mint
        mint_kp = Keypair()

        # PDA для метаданных
        metadata_pda, _ = PublicKey.find_program_address(
            [
                self.METADATA_SEED,
                bytes(self.MPL_TOKEN_METADATA),
                bytes(mint_kp.public_key),
            ],
            self.MPL_TOKEN_METADATA,
        )
        # PDA для bonding curve
        bonding_pda, _ = PublicKey.find_program_address(
            [self.BONDING_SEED, bytes(mint_kp.public_key)],
            self.PROGRAM_ID,
        )
        # ассоц. аккаунт, где лежат токены для bonding
        assoc_bonding = get_associated_token_address(
            mint_kp.public_key, bonding_pda
        )

        # формируем и отправляем транзакцию
        tx_sig = await self.program.rpc["create"](
            name,
            symbol,
            uri,
            self.keypair.public_key,  # authority
            ctx=Context(
                accounts={
                    "mint": mint_kp.public_key,
                    "associatedBondingCurve": assoc_bonding,
                    "metadata": metadata_pda,
                    "user": self.keypair.public_key,
                },
                signers=[mint_kp],
            ),
        )
        # ждём подтверждения
        await self.connection.confirm_transaction(tx_sig, commitment=Confirmed)

        return {
            "mint": str(mint_kp.public_key),
            "bonding_curve": str(bonding_pda),
            "tx": tx_sig,
        }
