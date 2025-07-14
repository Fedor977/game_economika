import subprocess
import sys
import os
import time


def run_game():
    """Запуск игры"""
    print("Запуск игровой экономики")

    # проверка на наличие файлов
    if not os.path.exists('server.py'):
        print("Файл server.py не найден")
        return

    if not os.path.exists('client.py'):
        print("Файл client.py не найден")
        return

    try:
        # запускаем сервер, должен запуститься на любой ос
        print("Запуск сервера")
        if os.name == 'nt':  # под винду
            server_process = subprocess.Popen([sys.executable, 'server.py'],
                                              creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:  # под линуху или мак
            server_process = subprocess.Popen([sys.executable, 'server.py'])

        # Ждем запуска сервера
        print("Ожидание запуска сервера")
        time.sleep(3)

        # тут запускаю клиент
        print("Запуск клиента")
        if os.name == 'nt':
            client_process = subprocess.Popen([sys.executable, 'client.py'],
                                              creationflags=subprocess.CREATE_NEW_CONSOLE)
        else: # под линуху или мак
            client_process = subprocess.Popen([sys.executable, 'client.py'])

        print("\nИгра запущена!!! Ура!")
        print("Сервер и клиент работают в разных окнах")
        print("Для остановки закройте окна или нажмите сtrl + с в этом окне")

        # жду завершения
        try:
            while True:
                if server_process.poll() is not None:
                    print("Сервер остановлен")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nОстановка игры")
            try:
                server_process.terminate()
                client_process.terminate()
            except:
                pass

    except Exception as e:
        print(f"Ошибка запуска: {e}")

    input("Нажмите Enter для выхода")


if __name__ == '__main__':
    run_game()