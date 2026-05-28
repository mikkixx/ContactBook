from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ContactBook.models import Contact
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Создает тестовые внешние контакты, привязанные к существующим сотрудникам (owner)'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=100, help='Количество контактов для создания (по умолчанию: 100)')
        parser.add_argument('--clear', action='store_true', help='Очистить таблицу контактов перед созданием новых')

    def handle(self, *args, **options):
        count = options['count']
        fake = Faker('ru_RU')

        if options['clear']:
            Contact.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Таблица контактов очищена'))

        # 🔍 Берём только активных сотрудников, чтобы назначать их владельцами
        users = list(User.objects.filter(employee_profile__is_deleted=False))

        if not users:
            self.stdout.write(self.style.ERROR('❌ В базе нет активных сотрудников! Сначала зарегистрируйте хотя бы одного пользователя через форму регистрации.'))
            return

        self.stdout.write(f'📊 Создание {count} тестовых внешних контактов...')
        self.stdout.write(f'👥 Найдено {len(users)} сотрудников для назначения владельцами.')

        categories = ['client', 'partner', 'supplier', 'other']
        organizations = [
            'ООО "Вектор"', 'АО "Прогресс"', 'ИП Смирнов', 'ЗАО "Техно"', 
            'ПАО "Финанс"', 'ООО "СтройГрупп"', 'АО "Логистик"'
        ]
        positions = [
            'Менеджер', 'Директор', 'Специалист', 'Бухгалтер', 
            'Инженер', 'Юрист', 'Маркетолог', 'Аналитик'
        ]

        created = 0
        skipped = 0

        for i in range(count):
            try:
                # Генерация уникальных данных
                phone = fake.phone_number()
                email = f"{fake.last_name().lower()}.{fake.first_name().lower()}{i}@test.com".replace('ё', 'е')

                # Пропускаем дубликаты
                if Contact.objects.filter(phone=phone).exists() or Contact.objects.filter(email=email).exists():
                    skipped += 1
                    continue

                # ✅ Всегда назначаем случайного активного сотрудника владельцем
                owner = random.choice(users)

                Contact.objects.create(
                    last_name=fake.last_name(),
                    first_name=fake.first_name(),
                    middle_name=fake.middle_name() if random.random() > 0.4 else None,
                    phone=phone,  # Модель автоматически нормализует телефон в save()
                    email=email if random.random() > 0.1 else None,
                    organization=random.choice(organizations) if random.random() > 0.3 else None,
                    position=random.choice(positions) if random.random() > 0.3 else None,
                    category=random.choice(categories),
                    owner=owner  # 🔗 Привязка к сотруднику
                )
                created += 1

                if created % 10 == 0:
                    self.stdout.write(f'  📝 Создано {created} контактов...')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ⚠️ Ошибка при создании контакта {i+1}: {e}'))
                skipped += 1

        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS(f'🎉 Готово! Создано {created} контактов.'))
        if skipped:
            self.stdout.write(self.style.WARNING(f'️ Пропущено {skipped} из-за дубликатов телефона/email.'))
        self.stdout.write(self.style.SUCCESS('='*50))