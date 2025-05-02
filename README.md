# Solana Auto Token Bot

Автоматизированный бот, который на основе новых твитов выбранного пользователя генерирует:
1. Краткое резюме (3 ключевых слова) с помощью OpenAI o4-mini.  
2. Иллюстрацию к резюме через DALL·E (Images API).  
3. Новый SPL-токен на Solana с bonding-curve (Pump.fun) и метаданными, включающими текст, ссылку на твит и URL картинки.  
4. Уведомление в один или несколько Telegram-чатов.

---

## Особенности

- **Реальное on-chain создание** токена и bonding-curve через Anchor-клиент (`anchorpy`).  
- Поддержка **Devnet** и **Mainnet-beta** (настраивается через `.env`).  
- Генерация текста и изображений через OpenAI API.  
- Мульти-чат-нотификации в Telegram.  
- Асинхронная архитектура для высокой пропускной способности.  

---

## Содержание репозитория

```text
.
├── .env.example         # Шаблон переменных окружения
├── Dockerfile           # Образ для контейнера
├── docker-compose.yml   # Сборка и запуск через Docker Compose
├── requirements.txt     # Python-зависимости
├── README.md            # Этот файл
└── src
    ├── main.py                  # Точка входа, управляет основным loop
    ├── twitter_watcher.py       # Асинхронный стриминг твитов
    ├── ai_summarizer.py         # Сжатие твита до ключевых слов (o4-mini)
    ├── ai_image_generator.py    # Генерация иллюстраций через DALL·E
    ├── ticker_generator.py      # Логика генерации трёхбуквенного тикера
    ├── pump_client.py           # On-chain вызовы Anchor-программы Pump.fun
    ├── telegram_notifier.py     # Рассылка сообщений в Telegram-чаты
    └── pump_idl.json            # IDL программы Pump.fun (Anchor interface)
