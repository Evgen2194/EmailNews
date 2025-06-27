import google.generativeai as genai
import os

# --- Шаг 1: Функция для выбора или ввода модели ---
def choose_model():
    """
    Позволяет пользователю выбрать модель из списка или ввести имя вручную.
    Возвращает строку с именем выбранной модели.
    """
    predefined_models = {
        "1": "gemini-1.5-pro-latest", # Используем -latest для автоматического получения последней стабильной версии 1.5 Pro
        "2": "gemini-2.5-pro-latest", # Используем -latest для 2.5 Pro (если доступна такая нотация, иначе gemini-2.5-pro)
        "3": "gemini-1.5-flash-latest" # Добавим Flash как еще один вариант
    }

    print("Доступные модели для выбора:")
    for key, model_name in predefined_models.items():
        print(f"{key}: {model_name}")
    print("0: Ввести имя модели вручную")

    while True:
        choice = input("Выберите номер модели или 0 для ручного ввода: ")
        if choice == "0":
            manual_model = input("Введите имя модели (например, 'gemini-1.5-pro'): ")
            if manual_model.strip():
                return manual_model.strip()
            else:
                print("Имя модели не может быть пустым. Попробуйте снова.")
        elif choice in predefined_models:
            return predefined_models[choice]
        else:
            print("Неверный выбор. Пожалуйста, выберите номер из списка или 0.")

# --- Основная часть скрипта (будет дополнена на следующих шагах) ---
def main():
    # Получение API ключа (предпочтительно из переменной окружения)
    # ЗАМЕНИТЕ 'YOUR_GEMINI_API_KEY' НА ВАШ КЛЮЧ, ЕСЛИ НЕ ИСПОЛЬЗУЕТЕ ПЕРЕМЕННУЮ ОКРУЖЕНИЯ
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = input("Пожалуйста, введите ваш Gemini API ключ: ")
        if not api_key:
            print("API ключ не предоставлен. Выход.")
            return

    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Ошибка конфигурации Gemini API: {e}")
        return

    selected_model_name = choose_model()
    print(f"\nВыбрана модель: {selected_model_name}")

    # --- Шаг 2 и 3: Интеграция и обработка ошибок (будут здесь) ---
    try:
        print(f"Инициализация модели: {selected_model_name}...")
        model = genai.GenerativeModel(selected_model_name)

        prompt = input("Введите ваш запрос к модели (например, 'привет'): ")
        if not prompt.strip():
            print("Запрос не может быть пустым. Выход.")
            return

        print("Генерация ответа...")
        response = model.generate_content(prompt)

        if response.parts:
            print("\nОтвет модели:")
            print(response.text)
        else:
            print("\nМодель не вернула контент. Возможно, запрос был заблокирован настройками безопасности.")
            if response.prompt_feedback:
                print(f"Prompt Feedback: {response.prompt_feedback}")


    except ValueError as ve:
        print(f"\nОшибка значения при работе с моделью '{selected_model_name}': {ve}")
        print("Возможно, указано некорректное имя модели или формат запроса не поддерживается.")
    except Exception as e:
        # Это более общая ошибка, которая может включать 404 от API, если модель не найдена
        print(f"\nПроизошла ошибка при работе с моделью '{selected_model_name}': {e}")
        print("Убедитесь, что имя модели указано верно, ваш API ключ действителен и имеет доступ к этой модели.")
        print("Также проверьте ваше интернет-соединение.")

if __name__ == "__main__":
    main()
