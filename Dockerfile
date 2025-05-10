FROM python:3.11-slim

# --- Устанавливаем зависимости для Chrome и Chromedriver ---
RUN apt-get update && apt-get install -y \
        wget gnupg2 unzip ca-certificates \
    && wget -qO- https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
         > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y \
        google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Chromedriver (версию под ваш Chrome)
RUN CHROME_VER=$(google-chrome --product-version | cut -d '.' -f 1) && \
    LATEST_DR=$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VER}) && \
    wget -O /tmp/chromedriver.zip \
         "https://chromedriver.storage.googleapis.com/${LATEST_DR}/chromedriver_linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver.zip

# --- Копируем и устанавливаем Python-зависимости ---
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники
COPY . .

# Точка входа
CMD ["python", "src/main.py"]
