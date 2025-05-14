# Solana Auto Token Bot

Автоматизированный бот, который на основе новых твитов выбранного пользователя генерирует:

1. **Краткое резюме** (3 ключевых слова) с помощью OpenAI o4-mini.  
2. **Иллюстрацию** к резюме через DALL·E (Images API).  
3. **Новый SPL-токен** на Solana с bonding-curve (Pump.fun) и метаданными, включающими текст, ссылку на твит и URL картинки.  
4. **Уведомление** в один или несколько Telegram-чатов.

---

## Особенности

- **Полный конвейер**: стриминг твитов → ИИ-сокращение → генерация изображения → on-chain mint → уведомления.  
- **Асинхронная архитектура** (`asyncio`) для высокой пропускной способности.  
- **Мульти-чат** рассылка в Telegram.  
- Поддержка **Devnet** и **Mainnet-beta** (настраивается через `.env`).  
- Лёгкая кастомизация тикера, параметров DALL·E и списка чатов.

---

## Структура репозитория

```
home/ubuntu/solana_token_bot/
├── .env.example        # Example environment file
├── .env                # Your actual environment variables (MUST BE KEPT SECRET)
├── requirements.txt    # Python dependencies
├── README.md           # This documentation file
├── todo.md             # Task checklist used during development
├── images/             # Directory for temporarily storing generated images before upload
└── src/
    ├── main.py             # Main orchestrator script for the bot
    ├── twitter_watcher.py  # Module for monitoring Twitter
    ├── ai_processor.py     # Module for OpenAI summarization and image generation
    ├── ticker_generator.py # Module for generating token tickers and names
    ├── selenium_pump_bot.py# Module for interacting with Pump.fun via Selenium
    └── telegram_notifier.py# Module for sending Telegram notifications
```

---

## Быстрый старт

1. **Клонировать репозиторий**  
   ```bash
   git clone https://github.com/ваш-аккаунт/solana-auto-tokenbot.git
   cd solana-auto-tokenbot
   ```

2. **Скопировать и настроить окружение**  
   ```bash
   cp .env.example .env
   ```
   Откройте `.env` и заполните:
   - `TWITTER_BEARER_TOKEN`  
   - `WATCH_TWITTER_USER`  
   - `OPENAI_API_KEY`  
   - `IMAGE_COUNT`, `IMAGE_SIZE`  
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_IDS`  
   - `SOLANA_RPC_ENDPOINT`, `SOLANA_KEYPAIR_PATH`

3. **Установить зависимости**  
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Скачать IDL Pump.fun**  
   ```bash
   mkdir -p src
   curl -L \
     https://gist.githubusercontent.com/rubpy/d8db121af1224a0e4a57f3a7a090f629/raw/pump_idl.json \
     -o src/pump_idl.json
   ```

5. **Запустить локально**  
   ```bash
   python src/main.py
   ```

---

## Запуск в Docker

1. **Собрать и запустить**  
   ```bash
   docker-compose up -d --build
   ```

2. **Логи**  
   ```bash
   docker-compose logs -f solana-auto-tokenbot
   ```

---

## Переменные окружения (`.env`)

| Переменная                | Описание                                                                 |
|---------------------------|--------------------------------------------------------------------------|
| `TWITTER_BEARER_TOKEN`    | Twitter API Bearer Token                                                 |
| `WATCH_TWITTER_USER`      | Никнейм пользователя (без `@`), чьи твиты бот отслеживает                |
| `OPENAI_API_KEY`          | Ключ OpenAI (Chat + Images API)                                          |
| `IMAGE_COUNT`             | Сколько изображений генерировать (DALL·E)                                 |
| `IMAGE_SIZE`              | Размер изображений (`256x256`,`512x512`,`1024x1024`)                     |
| `TELEGRAM_BOT_TOKEN`      | Токен вашего Telegram-бота                                               |
| `TELEGRAM_CHAT_IDS`       | Список chat_id через запятую                                             |
| `SOLANA_RPC_ENDPOINT`     | RPC-endpoint Solana (Devnet / Mainnet-beta)                               |
| `SOLANA_KEYPAIR_PATH`     | Путь до JSON-файла с приватным ключом Solana                              |

---

## Тестирование и отладка

1. **Devnet**  
   - В `.env`:  
     ```dotenv
     SOLANA_RPC_ENDPOINT=https://api.devnet.solana.com
     ```  
   - Аирдроп тестовых SOL:  
     ```bash
     solana airdrop 2 --keypair $SOLANA_KEYPAIR_PATH
     ```

2. **Unit-тесты**  
   - `generate_ticker`, `AISummarizer` (с моками OpenAI),  
   - `AIImageGenerator` (с моками),  
   - `TelegramNotifier` (с мок-ботом).

3. **End-to-end**  
   - Тестовый Twitter-аккаунт, Devnet,  
   - Запуск локально или в контейнере, публикация тестового твита, проверка создания токена и уведомлений.

---

## Рекомендации по продакшн-готовности

- **Обработка ошибок и retry** для всех внешних вызовов (Twitter API, OpenAI, Solana RPC).  
- **Метрики и мониторинг** (Prometheus, Sentry) для отслеживания uptime, ошибок и задержек.  
- **CI/CD**: автоматические тесты, линтинг (Black, Flake8), безопасность зависимостей.  
- **Безопасность**: не коммитьте `.env` в публичные репозитории, ротация ключей.

---

## Лицензия

MIT © rapuzan nookiqovich
