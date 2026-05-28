def normalize_phone(phone):
    if not phone:
        return ''

    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')

    if cleaned.startswith('8') and len(cleaned) == 11:
        cleaned = '+7' + cleaned[1:]
    elif cleaned.startswith('7') and len(cleaned) == 11 and not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    elif cleaned.startswith('+8') and len(cleaned) == 12:
        cleaned = '+7' + cleaned[2:]
    elif cleaned.startswith('+7') and len(cleaned) == 12:
        pass
    elif len(cleaned) == 10:
        cleaned = '+7' + cleaned
    else:
        if not cleaned.startswith('+'):
            cleaned = '+' + cleaned
    
    return cleaned


def format_phone_display(phone):
    if not phone:
        return ''

    normalized = normalize_phone(phone)
    
    digits = normalized.replace('+', '')
    
    if len(digits) == 11 and digits.startswith('7'):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    
    return normalized