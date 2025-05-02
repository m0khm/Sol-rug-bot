# src/pump_client.py

import os
import json
from pathlib import Path

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
    Поддерживает два способа загрузки ключа:
      1. Из переменной SOLANA_SECRET_KEY (Base58)
      2. Из JSON-файла по пути SOLANA_KEYPAIR_PATH
    """

    # ID программы Pump.fun
    PROGRAM_ID = PublicKey("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
    # Metaplex Token Metadata Program
    MPL_TOKEN_METADATA = PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
    # PDA seeds
    METADATA_SEED = b"metadata"
    BONDING_SEED = b"bonding-curve"

    def __init__(self):
        # RPC endpoint
        rpc_url = os.getenv("SOLANA_RPC_ENDPOINT")
        if not rpc_url:
            raise ValueError("SOLANA_RPC_ENDPOINT is not set in .env")

        # Load keypair
        secret_b58 = os.getenv("SOLANA_SECRET_KEY")
        if secret_b58:
            # если задан Base58-ключ
            secret_bytes = b58decode(secret_b58)
            self.keypair = Keypair.from_secret_key(secret_bytes)
        else:
            # иначе читаем JSON-файл
            path = os.getenv("SOLANA_KEYPAIR_PATH")
            if not path:
                raise ValueError("Either SOLANA_SECRET_KEY or SOLANA_KEYPAIR_PATH must be set")
            data = json.loads(Path(path).read_text())
            self.keypair = Keypair.from_secret_key(bytes(data))

        # Создаём асинхронное соединение и провайдера Anchor
        self.connection = AsyncClient(rpc_url, commitment=Confirmed)
        self.wallet = Wallet(self.keypair)
        self.provider = Provider(self.connection, self.wallet)

        # Загружаем IDL
        idl_path = Path("src/pump_idl.json")
        if not idl_path.exists():
            raise FileNotFoundError("pump_idl.json not found in src/")
        idl = json.loads(idl_path.read_text())
        self.program = Program(idl, self.PROGRAM_ID, self.provider)

    async def create_token(self, name: str, symbol: str, uri: str) -> dict:
        """
        Создаёт новый SPL-токен с bonding-curve в программе Pump.fun.

        :param name:       Название токена
        :param symbol:     Тикер (до 3 символов)
        :param uri:        URI метаданных (data: или IPFS/Arweave)
        :return:           Словарь с адресом mint, PDA bonding-curve и tx signature
        """
        # Генерируем новый mint
        mint_kp = Keypair()

        # PDA для Metaplex Metadata
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

        # Associated Token Account для bonding-curve
        assoc_bonding = get_associated_token_address(mint_kp.public_key, bonding_pda)

        # Вызываем инструкцию create
        tx_sig = await self.program.rpc["create"](
            name,
            symbol,
            uri,
            self.keypair.public_key,  # authority
            ctx=Context(
                accounts={
                    "mint":                   mint_kp.public_key,
                    "mintAuthority":          self.keypair.public_key,
                    "bondingCurve":           bonding_pda,
                    "associatedBondingCurve": assoc_bonding,
                    "global":                 self.provider.wallet.public_key,  # assume global account pre-initialized
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

        # Ждём подтверждения
        await self.connection.confirm_transaction(tx_sig, commitment=Confirmed)

        return {
            "mint":          str(mint_kp.public_key),
            "bonding_curve": str(bonding_pda),
            "tx":            tx_sig,
        }
