from django.contrib.auth.hashers import make_password, check_password
from .managers import AppointmentsManager, CustomerManager, ServiceManager, HairStockManager
from django.db import models

# Create your models here.
class Customer(models.Model):
    name = models.CharField(max_length=99)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=19)
    senha = models.CharField(max_length=128, default='temp')
    deleted = models.BooleanField(default=False)

    objects = CustomerManager()
    active_objects = models.Manager()

    def __str__(self):
        return self.name

    def set_password(self, raw_password):
        self.senha = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.senha)


class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration = models.IntegerField(help_text="Duração em minutos")

    objects = ServiceManager()

    def __str__(self):
        return self.name
    
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Agendado'),
        ('completed', 'Concluído'),
        ('canceled', 'Cancelado'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='appointments')
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, default='Rua Nelson Tigrão, 15, Vila Missionária, CEP: 04430-165')

    objects = AppointmentsManager()

    class Meta:
        ordering = ['scheduled_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__status_original = self.status

    def __str__(self):
        return f"{self.customer.name} - {self.scheduled_at:%d/%m/%Y %H:%M}"

    def save(self, *args, **kwargs):
        ja_tem_id_google = bool(self.google_event_id)
        status_antigo = self.__status_original

        super().save(*args, **kwargs)

        if self.status == 'scheduled' and not ja_tem_id_google:
            from .calendar_utils import criar_evento_google_calendar

            id_gerado = criar_evento_google_calendar(self)

            if id_gerado:
                self.google_event_id = id_gerado
                super().save(update_fields=['google_event_id'])

        elif self.status == 'canceled' and status_antigo != 'canceled' and self.google_event_id:
            from .calendar_utils import cancelar_evento_google_calendar
            cancelar_evento_google_calendar(self)

        self.__status_original = self.status


class AppointmentxService(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    applied_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.appointment.customer.name} - {self.service.name} at {self.appointment.scheduled_at:%d/%m/%Y %H:%M}"


class HairStock(models.Model):
    name = models.CharField(max_length=150)
    unit = models.CharField(max_length=20, default='un', help_text="Ex: un, pacote, g, m")
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity_on_hand = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_stock = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Alerta de estoque baixo quando quantity_on_hand ficar abaixo deste valor"
    )
    deleted = models.BooleanField(default=False)

    objects = HairStockManager()
    active_objects = models.Manager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.quantity_on_hand} {self.unit})"

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.minimum_stock


class ServiceHairStock(models.Model):
    """
    Define quanto de um item de estoque de cabelo é consumido sempre que
    um determinado serviço é agendado. Configurado via admin (inline em
    Service), é a base pra debitar o estoque automaticamente.
    """
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='hair_stock_usages')
    hair_stock = models.ForeignKey(HairStock, on_delete=models.PROTECT, related_name='service_usages')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantidade consumida por agendamento")

    class Meta:
        unique_together = ('service', 'hair_stock')

    def __str__(self):
        return f"{self.service.name} consome {self.quantity} {self.hair_stock.unit} de {self.hair_stock.name}"


class HairMovement(models.Model):
    MOVEMENT_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]

    hair_stock = models.ForeignKey(HairStock, on_delete=models.PROTECT, related_name='movements')
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price_at_time = models.DecimalField(max_digits=8, decimal_places=2)
    appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hair_movements',
        help_text="Preenchido quando a saída é consumo de um agendamento específico"
    )
    note = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sinal = '+' if self.movement_type == 'entrada' else '-'
        return f"{self.hair_stock.name}: {sinal}{self.quantity} em {self.created_at:%d/%m/%Y %H:%M}"