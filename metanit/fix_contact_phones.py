import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'metanit.settings')
django.setup()

from ContactBook.models import Contact
from ContactBook.utils import normalize_phone

def fix_contact_phones():
    print("🔍 Обновление телефонов внешних контактов...")
    updated = 0
    
    for contact in Contact.objects.all():
        original = contact.phone
        normalized = normalize_phone(original)
        
        if original != normalized:
            contact.phone = normalized
            contact.save(update_fields=['phone'])
            updated += 1
            print(f"{contact}: '{original}' → '{normalized}'")
    
    print(f"\nГотово! Обновлено {updated} номеров контактов")
    print("Теперь все телефоны в слитном формате: +79001234567")

if __name__ == '__main__':
    fix_contact_phones()