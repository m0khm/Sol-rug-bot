# src/pump_client.py

import os
import json
from pathlib import Path

# ── PATCH для httpx.AsyncClient proxy → proxies
import httpx
_orig = httpx.AsyncClient.__init__
def _patch(self, *args, proxy=None, **kwargs):
    if proxy is not None:
        kwargs["proxies"] = proxy
    return _orig(self, *args, **kwargs)
httpx.AsyncClient.__init__ = _patch
# ── END PATCH

from base58 import b58decode
from solana.rpc.async_api import AsyncClient
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Confirmed
from spl.token.instructions import get_associated_token_address
from anchorpy import Program, Provider, Wallet, Context, Idl

class PumpClient:
    PROGRAM_ID = PublicKey("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
    MPL_TOKEN_METADATA = PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
    METADATA_SEED = b"metadata"
    BONDING_SEED = b"bonding-curve"

    def __init__(self):
        rpc_url = os.getenv("SOLANA_RPC_ENDPOINT")
        if not rpc_url:
            raise ValueError("SOLANA_RPC_ENDPOINT не задан в .env")

        secret_b58 = os.getenv("SOLANA_SECRET_KEY")
        if secret_b58:
            secret = b58decode(secret_b58)
            self.keypair = Keypair.from_secret_key(secret)
        else:
            path = os.getenv("SOLANA_KEYPAIR_PATH")
            data = json.loads(Path(path).read_text())
            self.keypair = Keypair.from_secret_key(bytes(data))

        self.connection = AsyncClient(rpc_url, commitment=Confirmed)
        self.wallet     = Wallet(self.keypair)
        self.provider   = Provider(self.connection, self.wallet)

        idl_path = Path("src/pump_idl.json")
        idl_dict = json.loads(idl_path.read_text())
        idl = Idl.from_json(idl_dict)
        self.program = Program(idl, self.PROGRAM_ID, self.provider)

    async def create_token(self, name: str, symbol: str, uri: str) -> dict:
        mint_kp = Keypair()
        metadata_pda, _ = PublicKey.find_program_address(
            [self.METADATA_SEED, bytes(self.MPL_TOKEN_METADATA), bytes(mint_kp.public_key)],
            self.MPL_TOKEN_METADATA
        )
        bonding_pda, _ = PublicKey.find_program_address(
            [self.BONDING_SEED, bytes(mint_kp.public_key)], self.PROGRAM_ID
        )
        assoc = get_associated_token_address(mint_kp.public_key, bonding_pda)

        tx = await self.program.rpc["create"](
            name, symbol, uri, self.keypair.public_key,
            ctx=Context(
                accounts={
                    "mint":                   mint_kp.public_key,
                    "mintAuthority":          self.keypair.public_key,
                    "bondingCurve":           bonding_pda,
                    "associatedBondingCurve": assoc,
                    "global":                 self.provider.wallet.public_key,
                    "mplTokenMetadata":       self.MPL_TOKEN_METADATA,
                    "metadata":               metadata_pda,
                    "user":                   self.keypair.public_key,
                    "systemProgram":          PublicKey("11111111111111111111111111111111"),
                    "tokenProgram":           PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
                    "associatedTokenProgram": PublicKey("ATokenGPvoterCxoDvCk6Fg1UeCecud"),
                    "rent":                   PublicKey("SysvarRent111111111111111111111111111111111"),
                    "eventAuthority":         self.keypair.public_key,
                    "program":                self.PROGRAM_ID,
                },
                signers=[mint_kp],
            ),
        )
        await self.connection.confirm_transaction(tx, commitment=Confirmed)
        return {"mint": str(mint_kp.public_key), "bonding_curve": str(bonding_pda), "tx": tx}
