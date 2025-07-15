import socket
import json
import os
import time


class GameClient:
    """Основной класс игрового клиента"""

    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.current_account = None
        self.available_items = {}
        self.state = 'login'

    def connect(self):
        """Подключение к серверу"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"Подключено к серверу {self.host}:{self.port}")
            return True
        except socket.timeout:
            print("Ошибка: превышен таймаут подключения к серверу")
            return False
        except ConnectionRefusedError:
            print("Ошибка: сервер не запущен или недоступен")
            print("Убедитесь, что сервер запущен (python server.py)")
            return False
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False

    def disconnect(self):
        """Отключение от сервера"""
        if self.connected and self.socket:
            if self.current_account:
                self.send_request({'action': 'logout', 'nickname': self.current_account['nickname']})
            self.socket.close()
            self.connected = False
            print("Отключено от сервера")

    def send_request(self, request):
        """Отправка запроса на сервер"""
        if not self.connected:
            print("Не подключен к серверу")
            return None

        try:
            # отправляем запрос
            request_data = json.dumps(request, ensure_ascii=False)
            self.socket.send(request_data.encode('utf-8'))

            # получение ответа
            response_data = self.socket.recv(4096).decode('utf-8')

            if not response_data:
                print("Сервер разорвал соединение")
                self.connected = False
                return None

            response = json.loads(response_data)
            return response

        except ConnectionResetError:
            print("Соединение с сервером разорвано")
            self.connected = False
            return None
        except socket.timeout:
            print("Таймаут ответа от сервера")
            return None
        except json.JSONDecodeError:
            print("Ошибка декодирования ответа от сервера")
            return None
        except Exception as e:
            print(f"Ошибка отправки запроса: {e}")
            self.connected = False
            return None

    def clear_screen(self):
        """Очистка экрана"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        """Печать заголовка"""
        print("=" * 60)
        print("           ИГРОВАЯ ЭКОНОМИКА - METAGAMEPLAY")
        print("=" * 60)
        print()

    def print_account_info(self):
        """Печать информации об аккаунте"""
        if self.current_account:
            print(f"Игрок: {self.current_account['nickname']}")
            print(f"Кредиты: {self.current_account['credits']}")
            print("-" * 40)

    def login_state(self):
        """Состояние авторизации"""
        self.clear_screen()
        self.print_header()

        print("Введите ваш ник для входа в игру:")
        nickname = input("ник: ").strip()

        if not nickname:
            print("Nickname не может быть пустым!")
            input("Нажмите Enter для продолжения")
            return

        print("\nПодключение к серверу")

        # отправляем запрос на логин
        response = self.send_request({
            'action': 'login',
            'nickname': nickname
        })

        if response and response.get('status') == 'success':
            self.current_account = response['account']
            self.available_items = response['available_items']
            self.state = 'game_session'

            print(f"\nДобро пожаловать, {nickname}!")
            print(f"Бонус за вход: {response.get('login_bonus', 0)} кредитов")

        else:
            error_msg = response.get('message', 'Неизвестная ошибка') if response else 'Ошибка соединения'
            print(f"\nОшибка входа: {error_msg}")

        input("Нажмите Enter для продолжения")

    def game_session_state(self):
        """Состояние игровой сессии"""
        while self.state == 'game_session':
            self.clear_screen()
            self.print_header()
            self.print_account_info()

            print("Выберите действие:")
            print("1. Просмотр баланса")
            print("2. Список всех предметов")
            print("3. Мои предметы")
            print("4. Купить предмет")
            print("5. Продать предмет")
            print("6. Выйти из игры")
            print()

            choice = input("Ваш выбор (1-6): ").strip()

            if choice == '1':
                self.show_balance()
            elif choice == '2':
                self.show_all_items()
            elif choice == '3':
                self.show_my_items()
            elif choice == '4':
                self.buy_item()
            elif choice == '5':
                self.sell_item()
            elif choice == '6':
                self.logout()
            else:
                print("Неверный выбор!")
                input("Нажмите Enter для продолжения")

    def show_balance(self):
        """Показать баланс"""
        self.clear_screen()
        self.print_header()

        # Получаем актуальную информацию об аккаунте
        response = self.send_request({
            'action': 'get_account_info',
            'nickname': self.current_account['nickname']
        })

        if response and response.get('status') == 'success':
            account = response['account']
            print(f"Баланс игрока {account['nickname']}: {account['credits']} кредитов")
        else:
            print("Ошибка получения баланса")

        input("\nНажмите Enter для продолжения...")

    def show_all_items(self):
        """Показать все доступные предметы"""
        self.clear_screen()
        self.print_header()

        print("Все доступные предметы:")
        print("-" * 50)

        for item_id, item_info in self.available_items.items():
            print(f"{item_id.ljust(15)} | {item_info['name'].ljust(20)} | {item_info['price']} кредитов")

        input("\nНажмите Enter для продолжения")

    def show_my_items(self):
        """Показать предметы игрока"""
        self.clear_screen()
        self.print_header()

        print("Ваши предметы:")
        print("-" * 50)

        if not self.current_account['items']:
            print("У вас нет предметов")
        else:
            for item_id, quantity in self.current_account['items'].items():
                item_name = self.available_items.get(item_id, {}).get('name', 'Неизвестный предмет')
                print(f"{item_id.ljust(15)} | {item_name.ljust(20)} | Количество: {quantity}")

        input("\nНажмите Enter для продолжения...")

    def buy_item(self):
        """Купить предмет"""
        self.clear_screen()
        self.print_header()
        self.print_account_info()

        print("Доступные для покупки предметы:")
        print("-" * 50)

        for item_id, item_info in self.available_items.items():
            print(f"{item_id.ljust(15)} | {item_info['name'].ljust(20)} | {item_info['price']} кредитов")

        print("\nВведите ID предмета для покупки (или 'отмена' для выхода):")
        item_id = input("ID предмета: ").strip()

        if item_id.lower() == 'отмена':
            return

        if item_id not in self.available_items:
            print("Неверный ID предмета")
            input("Нажмите Enter для продолжения")
            return

        # Отправляем запрос на покупку
        response = self.send_request({
            'action': 'buy_item',
            'nickname': self.current_account['nickname'],
            'item_id': item_id
        })

        if response and response.get('status') == 'success':
            print(f"\n{response['message']}")
            self.current_account['credits'] = response['new_credits']
            self.current_account['items'] = response['items']
            print(f"Текущий баланс: {self.current_account['credits']} кредитов")
        else:
            error_msg = response.get('message', 'Неизвестная ошибка') if response else 'Ошибка соединения'
            print(f"\nОшибка покупки: {error_msg}")

        input("Нажмите Enter для продолжения")

    def sell_item(self):
        """Продать предмет"""
        self.clear_screen()
        self.print_header()
        self.print_account_info()

        if not self.current_account['items']:
            print("У вас нет предметов для продажи!")
            input("Нажмите Enter для продолжения...")
            return

        print("Ваши предметы:")
        print("-" * 50)

        for item_id, quantity in self.current_account['items'].items():
            item_name = self.available_items.get(item_id, {}).get('name', 'Неизвестный предмет')
            sell_price = self.available_items.get(item_id, {}).get('price', 0) // 2
            print(f"{item_id.ljust(15)} | {item_name.ljust(20)} | Количество: {quantity} | Цена продажи: {sell_price}")

        print("\nВведите ID предмета для продажи (или 'отмена' для выхода):")
        item_id = input("ID предмета: ").strip()

        if item_id.lower() == 'отмена':
            return

        if item_id not in self.current_account['items']:
            print("У вас нет этого предмета!")
            input("Нажмите Enter для продолжения...")
            return

        # Отправляем запрос на продажу
        response = self.send_request({
            'action': 'sell_item',
            'nickname': self.current_account['nickname'],
            'item_id': item_id
        })

        if response and response.get('status') == 'success':
            print(f"\n{response['message']}")
            self.current_account['credits'] = response['new_credits']
            self.current_account['items'] = response['items']
            print(f"Текущий баланс: {self.current_account['credits']} кредитов")
        else:
            error_msg = response.get('message', 'Неизвестная ошибка') if response else 'Ошибка соединения'
            print(f"\nОшибка продажи: {error_msg}")

        input("Нажмите Enter для продолжения")

    def logout(self):
        """Выход из игры"""
        self.send_request({
            'action': 'logout',
            'nickname': self.current_account['nickname']
        })

        self.current_account = None
        self.state = 'login'

        print("\nВы вышли из игры")
        input("Нажмите Enter для продолжения...")

    def wait_for_server(self, max_attempts=10):
        """Ожидание запуска сервера"""
        print("Проверка доступности сервера...")

        for attempt in range(max_attempts):
            if self.connect():
                return True

            if attempt == 0:
                print("Сервер недоступен. Попытка автоматического запуска")
                self.try_start_server()

            print(f"Попытка подключения {attempt + 1}/{max_attempts}")
            time.sleep(2)

        return False

    def try_start_server(self):
        """Попытка автоматического запуска сервера"""
        import subprocess
        import sys
        import os

        # Проверяем, есть ли файл server.py
        if os.path.exists('server.py'):
            try:
                print("Запуск сервера...")
                # Запускаем сервер в отдельном процессе
                if os.name == 'nt':  # Windows
                    subprocess.Popen([sys.executable, 'server.py'],
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:  # Linux/Mac
                    subprocess.Popen([sys.executable, 'server.py'])

                print("Сервер запущен. Ожидание инициализации")
                time.sleep(3)  # Даем время серверу запуститься

            except Exception as e:
                print(f"Не удалось автоматически запустить сервер {e}")
        else:
            print("Файл server.py не найден в текущей директории")

    def run(self):
        """Основной цикл клиента"""
        print("Запуск игрового клиента...")

        # Пытаемся подключиться с автоматическим запуском сервера
        if not self.wait_for_server():
            print("\nНе удалось подключиться к серверу.")
            print("\nВы можете:")
            print("1. Запустить сервер вручную: python server.py")
            print("2. Убедиться, что файл server.py находится в той же папке")
            print("3. Проверить, что порт 12345 свободен")
            input("\nНажмите Enter для выхода")
            return

        try:
            while self.connected:
                if self.state == 'login':
                    self.login_state()
                elif self.state == 'game_session':
                    self.game_session_state()
                else:
                    break

                # проверка соединения после каждой операции
                if not self.connected:
                    print("\nСоединение с сервером потеряно.")
                    print("Попробуйте перезапустить клиент.")
                    break

        except KeyboardInterrupt:
            print("\n\nВыход из игры")
        finally:
            self.disconnect()


if __name__ == '__main__':
    client = GameClient()
    client.run()
