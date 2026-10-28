from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria o superusuário padrão se ainda não houver um cadastrado."

    DEFAULT_USERNAME = "admin"
    DEFAULT_EMAIL = "admin@example.com"
    DEFAULT_PASSWORD = "12345"

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("Já existe um superusuário; nenhuma conta foi alterada.")
            return

        User.objects.create_superuser(
            self.DEFAULT_USERNAME,
            self.DEFAULT_EMAIL,
            self.DEFAULT_PASSWORD,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Superusuário "{self.DEFAULT_USERNAME}" criado com a senha padrão.'
        ))
