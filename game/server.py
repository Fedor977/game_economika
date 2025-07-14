#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Game Server - Основной сервер игровой экономики
Обрабатывает все операции с аккаунтами и предметами
"""

import socket
import threading
import json
import sqlite3
import random
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GameConfig:
    """Конфигурация игры"""

    # диапазон кредита при входе
    CREDITS_RANGE = (100, 500)

    # арсенал
    ITEMS = {
        'sword': {'name': 'Меч', 'price': 150},
        'shield': {'name': 'Щит', 'price': 120},
        'armor': {'name': 'Броня', 'price': 300},
        'bow': {'name': 'Лук', 'price': 200},
        'potion': {'name': 'Зелье здоровья', 'price': 50},
        'ship': {'name': 'Корабль', 'price': 1000},
        'cannon': {'name': 'Пушка', 'price': 400},
        'treasure_map': {'name': 'Карта сокровищ', 'price': 250},
        'compass': {'name': 'Компас', 'price': 80},
        'rope': {'name': 'Веревка', 'price': 30}
    }


class DatabaseManager:
    """Менеджер базы данных для работы с аккаунтами"""

    def __init__(self, db_path='game_database.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # создание таблицы аккаунтов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT UNIQUE NOT NULL,
                credits INTEGER DEFAULT 0,
                last_login TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # создание таблицы предметов игроков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                item_id TEXT,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")

    def get_account(self, nickname):
        """Получение аккаунта по nickname"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM accounts WHERE nickname = ?', (nickname,))
        account = cursor.fetchone()

        if account:
            # получение предметов игрока
            cursor.execute('''
                SELECT item_id, quantity FROM player_items 
                WHERE account_id = ?
            ''', (account[0],))
            items = {item[0]: item[1] for item in cursor.fetchall()}

            account_data = {
                'id': account[0],
                'nickname': account[1],
                'credits': account[2],
                'last_login': account[3],
                'items': items
            }
        else:
            account_data = None

        conn.close()
        return account_data

    def create_account(self, nickname):
        """Создание нового аккаунта"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO accounts (nickname, credits, last_login) 
                VALUES (?, 0, ?)
            ''', (nickname, datetime.now().isoformat()))

            account_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Создан новый аккаунт {nickname}")
            return self.get_account(nickname)

        except sqlite3.IntegrityError:
            logger.error(f"Аккаунт {nickname} уже существует")
            return None
        finally:
            conn.close()

    def update_credits(self, account_id, new_credits):
        """Обновление кредитов аккаунта"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE accounts SET credits = ?, last_login = ? 
            WHERE id = ?
        ''', (new_credits, datetime.now().isoformat(), account_id))

        conn.commit()
        conn.close()

    def add_item(self, account_id, item_id):
        """Добавление предмета игроку"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # проверяем, есть ли уже такой предмет
        cursor.execute('''
            SELECT quantity FROM player_items 
            WHERE account_id = ? AND item_id = ?
        ''', (account_id, item_id))

        existing = cursor.fetchone()

        if existing:
            # увеличиваем количество
            cursor.execute('''
                UPDATE player_items SET quantity = quantity + 1 
                WHERE account_id = ? AND item_id = ?
            ''', (account_id, item_id))
        else:
            # добавляем новый предмет
            cursor.execute('''
                INSERT INTO player_items (account_id, item_id, quantity) 
                VALUES (?, ?, 1)
            ''', (account_id, item_id))

        conn.commit()
        conn.close()

    def remove_item(self, account_id, item_id):
        """Удаление предмета у игрока"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT quantity FROM player_items 
            WHERE account_id = ? AND item_id = ?
        ''', (account_id, item_id))

        existing = cursor.fetchone()

        if existing and existing[0] > 1:
            # уменьшить количество
            cursor.execute('''
                UPDATE player_items SET quantity = quantity - 1 
                WHERE account_id = ? AND item_id = ?
            ''', (account_id, item_id))
        elif existing:
            # удаление предмета
            cursor.execute('''
                DELETE FROM player_items 
                WHERE account_id = ? AND item_id = ?
            ''', (account_id, item_id))

        conn.commit()
        conn.close()


class GameServer:
    """Основной класс игрового сервера"""

    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.db_manager = DatabaseManager()
        self.active_sessions = {}

    def start(self):
        """Запуск сервера"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            logger.info(f"Сервер запущен на {self.host}:{self.port}")
            print(f"Игровой сервер запущен на {self.host}:{self.port}")
            print("Ожидание подключения клиентов...")
            print("Для остановки нажмите Ctrl+C")
            print("-" * 50)

            while True:
                try:
                    client_socket, addr = server_socket.accept()
                    logger.info(f"Подключен клиент: {addr}")

                    # создается новый поток для каждого клиента
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.error as e:
                    logger.error(f"Ошибка сокета: {e}")
                    continue

        except OSError as e:
            if e.errno == 10048:
                print(f"Ошибка: порт {self.port} уже используется")
                print("Возможно, сервер уже запущен или порт занят другим приложением")
            else:
                print(f"Ошибка запуска сервера: {e}")
        except KeyboardInterrupt:
            logger.info("Сигнал об остановке игрового сервера")
            print("\nОстановка сервера")
        finally:
            server_socket.close()
            logger.info("Сервер остановлен")

    def handle_client(self, client_socket, addr):
        """Обработка клиента"""
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break

                try:
                    request = json.loads(data)
                    response = self.process_request(request)

                    client_socket.send(json.dumps(response, ensure_ascii=False).encode('utf-8'))

                except json.JSONDecodeError:
                    error_response = {'status': 'error', 'message': 'Неверный формат JSON'}
                    client_socket.send(json.dumps(error_response).encode('utf-8'))

        except Exception as e:
            logger.error(f"Ошибка обработки клиента {addr}: {e}")
        finally:
            client_socket.close()
            logger.info(f"Клиент {addr} отключен")

    def process_request(self, request):
        """Обработка запроса от клиента"""
        action = request.get('action')

        if action == 'login':
            return self.handle_login(request)
        elif action == 'logout':
            return self.handle_logout(request)
        elif action == 'get_items':
            return self.handle_get_items(request)
        elif action == 'buy_item':
            return self.handle_buy_item(request)
        elif action == 'sell_item':
            return self.handle_sell_item(request)
        elif action == 'get_account_info':
            return self.handle_get_account_info(request)
        else:
            return {'status': 'error', 'message': f'Неизвестное действие: {action}'}

    def handle_login(self, request):
        """Обработка логина"""
        nickname = request.get('nickname')
        if not nickname:
            return {'status': 'error', 'message': 'Не указан nickname'}

        # получить или создать аккаунт
        account = self.db_manager.get_account(nickname)
        if not account:
            account = self.db_manager.create_account(nickname)
            if not account:
                return {'status': 'error', 'message': 'Не удалось создать аккаунт'}

        # начисление кредитов за взод в игру
        login_bonus = random.randint(*GameConfig.CREDITS_RANGE)
        new_credits = account['credits'] + login_bonus

        self.db_manager.update_credits(account['id'], new_credits)
        account['credits'] = new_credits

        # Сохраняем сессию
        self.active_sessions[nickname] = account

        logger.info(f"Игрок {nickname} вошел в игру. Бонус: {login_bonus} кредитов")

        return {
            'status': 'success',
            'account': {
                'nickname': account['nickname'],
                'credits': account['credits'],
                'items': account['items']
            },
            'login_bonus': login_bonus,
            'available_items': GameConfig.ITEMS
        }

    def handle_logout(self, request):
        """Обработка выхода"""
        nickname = request.get('nickname')
        if nickname in self.active_sessions:
            del self.active_sessions[nickname]
            logger.info(f"Игрок {nickname} вышел из игры")

        return {'status': 'success', 'message': 'Выход выполнен'}

    def handle_get_items(self, request):
        """Получение списка всех доступных предметов"""
        return {
            'status': 'success',
            'items': GameConfig.ITEMS
        }

    def handle_buy_item(self, request):
        """Покупка предмета"""
        nickname = request.get('nickname')
        item_id = request.get('item_id')

        if nickname not in self.active_sessions:
            return {'status': 'error', 'message': 'Не авторизован'}

        if item_id not in GameConfig.ITEMS:
            return {'status': 'error', 'message': 'Неизвестный предмет'}

        account = self.active_sessions[nickname]
        item_price = GameConfig.ITEMS[item_id]['price']

        if account['credits'] < item_price:
            return {'status': 'error', 'message': 'Недостаточно кредитов'}

        # Покупаем предмет
        new_credits = account['credits'] - item_price
        self.db_manager.update_credits(account['id'], new_credits)
        self.db_manager.add_item(account['id'], item_id)

        # Обновляем сессию
        account['credits'] = new_credits
        if item_id in account['items']:
            account['items'][item_id] += 1
        else:
            account['items'][item_id] = 1

        logger.info(f"Игрок {nickname} купил {item_id} за {item_price} кредитов")

        return {
            'status': 'success',
            'message': f'Предмет {GameConfig.ITEMS[item_id]["name"]} куплен',
            'new_credits': new_credits,
            'items': account['items']
        }

    def handle_sell_item(self, request):
        """Продажа предмета"""
        nickname = request.get('nickname')
        item_id = request.get('item_id')

        if nickname not in self.active_sessions:
            return {'status': 'error', 'message': 'Не авторизован'}

        if item_id not in GameConfig.ITEMS:
            return {'status': 'error', 'message': 'Неизвестный предмет'}

        account = self.active_sessions[nickname]

        if item_id not in account['items'] or account['items'][item_id] <= 0:
            return {'status': 'error', 'message': 'У вас нет этого предмета. Факир был пьян ( '}

        # Продаем предмет за половину цены
        item_price = GameConfig.ITEMS[item_id]['price'] // 2
        new_credits = account['credits'] + item_price

        self.db_manager.update_credits(account['id'], new_credits)
        self.db_manager.remove_item(account['id'], item_id)

        # обнова сессии
        account['credits'] = new_credits
        account['items'][item_id] -= 1
        if account['items'][item_id] <= 0:
            del account['items'][item_id]

        logger.info(f"Игрок {nickname} продал {item_id} за {item_price} кредитов")

        return {
            'status': 'success',
            'message': f'Предмет {GameConfig.ITEMS[item_id]["name"]} продан за {item_price} кредитов',
            'new_credits': new_credits,
            'items': account['items']
        }

    def handle_get_account_info(self, request):
        """Получение информации об аккаунте"""
        nickname = request.get('nickname')

        if nickname not in self.active_sessions:
            return {'status': 'error', 'message': 'Не авторизован'}

        account = self.active_sessions[nickname]
        return {
            'status': 'success',
            'account': {
                'nickname': account['nickname'],
                'credits': account['credits'],
                'items': account['items']
            }
        }


if __name__ == '__main__':
    server = GameServer()
    server.start()
