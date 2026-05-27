import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'metanit.settings')
django.setup()

from ContactBook.models import Employee
from ContactBook.utils import normalize_phone

def fix_all_phones():
    updated = 0
    for emp in Employee.objects.all():
        original = emp.phone
        normalized = normalize_phone(original)
        if original != normalized:
            emp.phone = normalized
            emp.save(update_fields=['phone'])
            updated += 1
            print(f"✅ {emp}: '{original}' → '{normalized}'")
    print(f"\n🎉 Готово! Обновлено {updated} номеров")

if __name__ == '__main__':
    fix_all_phones()