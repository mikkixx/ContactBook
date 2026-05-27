from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ContactBook.models import Contact
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Создает тестовые внешние контакты для проверки функционала'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Количество контактов для создания (по умолчанию: 100)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить все существующие внешние контакты перед созданием новых'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']
        fake = Faker('ru_RU')
        
        if clear:
            self.stdout.write(self.style.WARNING('🗑️ Очистка таблицы внешних контактов...'))
            Contact.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Таблица очищена'))

        self.stdout.write(f'📊 Создание {count} тестовых внешних контактов...')

        # === Категории контактов ===
        categories = ['client', 'partner', 'supplier', 'other']
        category_labels = {
            'client': 'Клиент',
            'partner': 'Партнёр', 
            'supplier': 'Поставщик',
            'other': 'Другое'
        }

        # === Организации для генерации ===
        organizations = [
            'ООО "ТехноСервис"', 'АО "СтройИнвест"', 'ИП Петров А.В.',
            'ЗАО "ЛогистикГрупп"', 'ООО "ФинансКонсалт"', 'ПАО "ЭнергоСбыт"',
            'ООО "МедиаПлюс"', 'ИП Сидорова Е.К.', 'ООО "АвтоТранс"',
            'ЗАО "ПромКомплект"', 'ООО "СофтДев"', 'ИП Иванов И.И.',
            'ПАО "БанкСтолица"', 'ООО "ТорговыйДом"', 'ЗАО "АгроХолдинг"',
            'ООО "КлинингПро"', 'ИП Козлов М.С.', 'ООО "РекламаОнлайн"',
            'ЗАО "СтальКонструк"', 'ООО "ФудСервис"'
        ]

        positions = [
            'Менеджер', 'Директор', 'Специалист', 'Руководитель отдела',
            'Инженер', 'Бухгалтер', 'Юрист', 'Маркетолог', 'Аналитик',
            'Консультант', 'Техник', 'Координатор', 'Представитель',
            'Начальник', 'Заместитель директора', 'Главный специалист'
        ]

        created_count = 0
        skipped_count = 0
        
        # Получаем список пользователей для назначения владельцев (опционально)
        users = list(User.objects.all())

        for i in range(count):
            try:
                # Генерируем данные
                last_name = fake.last_name()
                first_name = fake.first_name()
                middle_name = fake.middle_name() if random.random() > 0.3 else None
                phone = fake.phone_number()
                
                # Генерируем уникальный email
                email_domain = random.choice(['example.com', 'test.ru', 'mail.test', 'demo.org'])
                email = f"{last_name.lower()}.{first_name.lower()}{i}@{email_domain}".replace('ё', 'е')
                
                # Организация (70% контактов имеют организацию)
                organization = random.choice(organizations) if random.random() > 0.3 else None
                
                # Должность (если есть организация — должность вероятнее)
                position = random.choice(positions) if organization and random.random() > 0.2 else None
                
                # Категория
                category = random.choice(categories)
                
                # Владелец (опционально, 50% контактов имеют владельца)
                owner = random.choice(users) if users and random.random() > 0.5 else None

                # Проверяем уникальность телефона и email перед созданием
                if Contact.objects.filter(phone=phone).exists():
                    skipped_count += 1
                    continue
                if email and Contact.objects.filter(email=email).exists():
                    skipped_count += 1
                    continue

                # Создаём контакт
                contact = Contact.objects.create(
                    last_name=last_name,
                    first_name=first_name,
                    middle_name=middle_name,
                    phone=phone,
                    email=email if random.random() > 0.1 else None,  # 10% без email
                    organization=organization,
                    position=position,
                    category=category,
                    owner=owner
                )
                
                created_count += 1
                
                if created_count % 10 == 0:
                    self.stdout.write(f'  👤 Создано {created_count} контактов...')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ⚠️ Ошибка при создании контакта {i+1}: {e}'))
                skipped_count += 1
                continue

        # === Итоговая статистика ===
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('✅ Готово!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Всего создано контактов: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'⚠️ Пропущено (дубликаты): {skipped_count}'))
        self.stdout.write(self.style.SUCCESS(f'📄 Всего страниц (по 10 на странице): {(created_count + 9) // 10}'))
        self.stdout.write(self.style.SUCCESS('='*50))
        
        # Статистика по категориям
        from django.db.models import Count
        stats = Contact.objects.values('category').annotate(
            count=Count('id')
        ).order_by('category')
        
        self.stdout.write(self.style.WARNING('\n📈 Распределение по категориям:'))
        for stat in stats:
            label = category_labels.get(stat['category'], stat['category'])
            self.stdout.write(f'   {label}: {stat["count"]}')