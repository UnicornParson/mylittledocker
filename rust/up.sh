#!/bin/bash

# 1. Загрузка переменных из файла .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 2. Проверка наличия DATA_PATH в окружении
if [ -z "$DATA_PATH" ]; then
    echo "Ошибка: DATA_PATH не задана в файле .env"
    exit 1
fi

# 3. Проверка существования папки и создание, если нужно
if [ ! -d "$DATA_PATH" ]; then
    echo "Папка $DATA_PATH не существует. Создаю..."
    mkdir -p "$DATA_PATH"
fi

# 4. Настройка прав для пользователя контейнера (UID 4711)
echo "Настраиваю права доступа для $DATA_PATH..."
sudo chown -R 4711 "$DATA_PATH"

# 5. Определение имени контейнера
CONTAINER_NAME="rust-server"

# 6. Остановка и удаление существующего контейнера
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}$"; then
    echo "Контейнер $CONTAINER_NAME уже существует. Останавливаю и удаляю..."
    docker stop $CONTAINER_NAME > /dev/null 2>&1
    docker rm $CONTAINER_NAME > /dev/null 2>&1
fi

# 7. Создание и запуск нового контейнера
echo "Создаю и запускаю новый контейнер $CONTAINER_NAME..."
docker create -it --restart always \
    --name $CONTAINER_NAME \
    -p 28015:28015/udp \
    -p 28015:28015/tcp \
    -p 28082:28082/tcp \
    -v "$DATA_PATH":/home/ips-hosting \
    ipshosting/game-rust:v4

docker start $CONTAINER_NAME

# 8. Проверка статуса
if [ $? -eq 0 ]; then
    echo "✅ Сервер Rust успешно запущен в контейнере $CONTAINER_NAME"
    echo "📁 Данные сохраняются в: $DATA_PATH"
    echo "🔌 Игровой порт: 28015"
else
    echo "❌ Ошибка при запуске контейнера"
    exit 1
fi