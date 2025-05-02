# src/pump_client.py

import os
import json
from pathlib import Path

# ── PATCH: залатать httpx.AsyncClient, чтобы принимал proxy
import httpx
_orig_ac_init = httpx.AsyncClient.__init__
def _patched_ac_init(self, *args, proxy=None, **kwargs):
    if proxy is not None:
        # httpx теперь ожидает аргумент proxies, а не proxy
        kwargs["proxies"] = proxy
    return _orig_ac_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = _patched_ac_init
# ── END PATCH

from base58 import b58decode
from solana.rpc.async_api import AsyncClient
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Confirmed
from spl.token.instructions import get_associated_token_address
from anchorpy import Program, Provider, Wallet, Context


class PumpClient:
    """
    Клиент для on-chain программы Pump.fun на Solana.
    Загружает Keypair из SOLANA_SECRET_KEY (Base58) или из JSON-файла.
    """

    PROGRAM_ID = PublicKey("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
    MPL_TOKEN_METADATA = PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
    METADATA_SEED = b"metadata"
    BONDING_SEED = b"bonding-curve"

    def __init__(self):
        rpc_url = os.getenv("SOLANA_RPC_ENDPOINT")
        if not rpc_url:
            raise ValueError("SOLANA_RPC_ENDPOINT is not set")

        secret_b58 = os.getenv("SOLANA_SECRET_KEY")
        if secret_b58:
            secret_bytes = b58decode(secret_b58)
            self.keypair = Keypair.from_secret_key(secret_bytes)
        else:
            path = os.getenv("SOLANA_KEYPAIR_PATH")
            if not path:
                raise ValueError("Provide SOLANA_SECRET_KEY or SOLANA_KEYPAIR_PATH")
            data = json.loads(Path(path).read_text())
            self.keypair = Keypair.from_secret_key(bytes(data))

        # благодаря патчу в начале теперь не упадёт на proxy
        self.connection = AsyncClient(rpc_url, commitment=Confirmed)
        self.wallet     = Wallet(self.keypair)
        self.provider   = Provider(self.connection, self.wallet)

        idl_path = Path("src/pump_idl.json")
        if not idl_path.exists():
            raise FileNotFoundError("pump_idl.json not found")
        idl = json.loads(idl_path.read_text())
        self.program = Program(idl, self.PROGRAM_ID, self.provider)

    async def create_token(self, name: str, symbol: str, uri: str) -> dict:
        mint_kp = Keypair()

        metadata_pda, _ = PublicKey.find_program_address(
            [self.METADATA_SEED, bytes(self.MPL_TOKEN_METADATA), bytes(mint_kp.public_key)],
            self.MPL_TOKEN_METADATA,
        )
        bonding_pda, _ = PublicKey.find_program_address(
            [self.BONDING_SEED, bytes(mint_kp.public_key)], self.PROGRAM_ID
        )
        assoc_bonding = get_associated_token_address(mint_kp.public_key, bonding_pda)

        tx_sig = await self.program.rpc["create"](
            name,
            symbol,
            uri,
            self.keypair.public_key,
            ctx=Context(
                accounts={
                    "mint":                   mint_kp.public_key,
                    "mintAuthority":          self.keypair.public_key,
                    "bondingCurve":           bonding_pda,
                    "associatedBondingCurve": assoc_bonding,
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

        await self.connection.confirm_transaction(tx_sig, commitment=Confirmed)
        return {
            "mint":          str(mint_kp.public_key),
            "bonding_curve": str(bonding_pda),
            "tx":            tx_sig,
        }
