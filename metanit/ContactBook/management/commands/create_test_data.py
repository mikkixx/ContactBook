from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ContactBook.models import Employee, Department, Subdivision
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Создает тестовых сотрудников для проверки пагинации и функционала'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Количество сотрудников для создания (по умолчанию: 100)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить всех существующих сотрудников перед созданием новых'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']
        fake = Faker('ru_RU')
        
        if clear:
            self.stdout.write(self.style.WARNING('🗑️ Очистка базы данных...'))
            Employee.objects.all().delete()
            User.objects.all().delete()
            Department.objects.all().delete()
            Subdivision.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ База очищена'))

        self.stdout.write(f'📊 Создание {count} тестовых сотрудников...')

        # === Создаем отделы ===
        departments = []
        dept_names = [
            'IT', 'HR', 'Бухгалтерия', 'Продажи', 'Маркетинг', 
            'Логистика', 'Юридический', 'Производство', 'Закупки'
        ]
        
        for name in dept_names:
            dept, created = Department.objects.get_or_create(name=name)
            departments.append(dept)
            if created:
                self.stdout.write(f'  ✅ Отдел: {name}')

        # === Создаем подразделения ===
        subdivisions = []
        sub_data = {
            'IT': ['Разработка', 'Тестирование', 'Поддержка', 'DevOps'],
            'HR': ['Рекрутинг', 'Обучение и развитие', 'HR-администрирование'],
            'Продажи': ['B2B продажи', 'B2C продажи', 'Корпоративные клиенты'],
            'Маркетинг': ['Digital-маркетинг', 'PR и коммуникации', 'Аналитика'],
            'Производство': ['Цех №1', 'Цех №2', 'Контроль качества'],
        }
        
        for dept_name, sub_names in sub_data.items():
            try:
                dept = Department.objects.get(name=dept_name)
                for sub_name in sub_names:
                    sub, created = Subdivision.objects.get_or_create(
                        name=sub_name,
                        department=dept
                    )
                    subdivisions.append(sub)
                    if created:
                        self.stdout.write(f'    ↳ Подразделение: {sub_name}')
            except Department.DoesNotExist:
                pass

        self.stdout.write(self.style.SUCCESS(f'✅ Создано {len(subdivisions)} подразделений'))

        # === Создаем сотрудников ===
        positions = [
            'Менеджер', 'Специалист', 'Старший специалист', 
            'Руководитель отдела', 'Директор', 'Аналитик',
            'Разработчик', 'Тестировщик', 'Консультант',
            'Инженер', 'Техник', 'Координатор'
        ]

        created_count = 0
        for i in range(count):
            try:
                # Генерируем данные
                last_name = fake.last_name()
                first_name = fake.first_name()
                middle_name = fake.middle_name()
                email = f"employee{i+1:03d}@test.com"  # employee001@test.com
                username = f"employee{i+1:03d}"
                password = 'test123'
                
                # Создаем пользователя
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True  # Активен сразу
                )
                
                # Выбираем случайные отдел и подразделение
                dept = random.choice(departments)
                
                # 70% сотрудников имеют подразделение, 30% - нет
                if random.random() > 0.3 and subdivisions:
                    # Выбираем подразделение из того же отдела (если есть)
                    dept_subs = [s for s in subdivisions if s.department == dept]
                    sub = random.choice(dept_subs) if dept_subs else random.choice(subdivisions)
                else:
                    sub = None
                
                # Создаем сотрудника
                employee = Employee.objects.create(
                    user_account=user,
                    last_name=last_name,
                    first_name=first_name,
                    middle_name=middle_name,
                    department=dept,
                    subdivision=sub,
                    position=random.choice(positions),
                    phone=fake.phone_number(),
                    floor=str(random.randint(1, 10)),
                    cabinet=str(random.randint(100, 500)),
                    role='admin' if i == 0 else 'user'  # Первый сотрудник - админ
                )
                
                created_count += 1
                
                if created_count % 10 == 0:
                    self.stdout.write(f'  👤 Создано {created_count} сотрудников...')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ⚠️ Ошибка при создании сотрудника {i+1}: {e}'))
                continue

        # === Итоговая статистика ===
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('✅ Готово!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Всего создано сотрудников: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'📄 Всего страниц (по 10 на странице): {(created_count + 9) // 10}'))
        self.stdout.write(self.style.SUCCESS('='*50))
        
        self.stdout.write(self.style.WARNING('\n🔑 Данные для входа:'))
        self.stdout.write(self.style.SUCCESS('   Логин: employee001 / Пароль: test123 (АДМИНИСТРАТОР)'))
        self.stdout.write(self.style.SUCCESS('   Логин: employee002 / Пароль: test123 (обычный пользователь)'))
        self.stdout.write(self.style.SUCCESS('   Логин: employee003 / Пароль: test123'))
        self.stdout.write(self.style.SUCCESS('   ... и так далее'))