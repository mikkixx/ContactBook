# ContactBook/utils.py

def normalize_phone(phone):
    """
    Приводит номер телефона к единому формату: +79001234567
    """
    if not phone:
        return ''
    
    # Удаляем всё кроме цифр и знака +
    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Если начинается с 8 или +7, приводим к +7
    if cleaned.startswith('8') and len(cleaned) == 11:
        cleaned = '+7' + cleaned[1:]
    elif cleaned.startswith('7') and len(cleaned) == 11 and not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    elif cleaned.startswith('+8') and len(cleaned) == 12:
        cleaned = '+7' + cleaned[2:]
    elif cleaned.startswith('+7') and len(cleaned) == 12:
        pass  # Уже в правильном формате
    elif len(cleaned) == 10:  # Без кода страны
        cleaned = '+7' + cleaned
    else:
        # Если не удалось распознать — возвращаем как есть, но с +
        if not cleaned.startswith('+'):
            cleaned = '+' + cleaned
    
    return cleaned


def format_phone_display(phone):
    """
    Форматирует номер для красивого отображения: +7 (900) 123-45-67
    """
    if not phone:
        return ''
    
    # Сначала нормализуем
    normalized = normalize_phone(phone)
    
    # Убираем + для парсинга
    digits = normalized.replace('+', '')
    
    if len(digits) == 11 and digits.startswith('7'):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    
    return normalized  # Если не российский формат — возвращаем как есть