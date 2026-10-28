from django.contrib.auth.hashers import make_password, check_password
from .managers import AppointmentsManager, CustomerManager, ServiceManager, HairStockManager
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal

# Create your models here.
class Customer(models.Model):
    name = models.CharField('Nome', max_length=99)
    email = models.EmailField('E-mail', unique=True)
    phone = models.CharField('Telefone', max_length=19)
    senha = models.CharField('Senha', max_length=128, default='temp')
    deleted = models.BooleanField('Excluído', default=False)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    objects = CustomerManager()
    active_objects = models.Manager()

    def __str__(self):
        return self.name

    def set_password(self, raw_password):
        self.senha = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.senha)


class Service(models.Model):
    name = models.CharField('Nome', max_length=100)
    description = models.TextField('Descrição')
    price = models.DecimalField('Preço', max_digits=8, decimal_places=2)
    duration = models.IntegerField('Duração', help_text="Duração em minutos")

    objects = ServiceManager()

    class Meta:
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'

    def __str__(self):
        return self.name
    
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Agendado'),
        ('completed', 'Concluído'),
        ('canceled', 'Cancelado'),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='appointments', verbose_name='Cliente'
    )
    scheduled_at = models.DateTimeField('Data e hora')
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='scheduled')
    google_event_id = models.CharField('ID do evento no Google Calendar', max_length=255, blank=True, null=True)
    location = models.CharField(
        'Local de atendimento',
        max_length=255,
        default='Rua Nelson Tigrão, 15, Vila Missionária, CEP: 04430-165',
    )

    objects = AppointmentsManager()

    class Meta:
        ordering = ['scheduled_at']
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'

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
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, verbose_name='Agendamento')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name='Serviço')
    applied_price = models.DecimalField('Preço aplicado', max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = 'Serviço do agendamento'
        verbose_name_plural = 'Serviços do agendamento'

    def __str__(self):
        return f"{self.appointment.customer.name} - {self.service.name} em {self.appointment.scheduled_at:%d/%m/%Y %H:%M}"


class HairStock(models.Model):
    name = models.CharField('Item de estoque', max_length=150)
    unit = models.CharField(
        'Unidade', max_length=20, default='un', help_text="Ex: un, pacote, g, m"
    )
    consumption_unit = models.CharField(
        'Unidade de consumo',
        max_length=20,
        blank=True,
        default='',
        help_text="Unidade usada no consumo por serviço; vazia usa a unidade do estoque.",
    )
    consumption_factor = models.DecimalField(
        'Consumo por unidade de estoque',
        max_digits=12,
        decimal_places=4,
        default=Decimal('1'),
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="Quantidade na unidade de consumo contida em uma unidade de estoque.",
    )
    unit_price = models.DecimalField('Preço unitário', max_digits=8, decimal_places=2)
    quantity_on_hand = models.DecimalField(
        'Quantidade disponível', max_digits=10, decimal_places=6, default=0
    )
    minimum_stock = models.DecimalField(
        'Estoque mínimo',
        max_digits=10, decimal_places=6, default=0,
        help_text="Alerta de estoque baixo quando a quantidade disponível ficar igual ou abaixo deste valor"
    )
    deleted = models.BooleanField('Excluído', default=False)

    objects = HairStockManager()
    active_objects = models.Manager()

    class Meta:
        ordering = ['name']
        verbose_name = 'Item de estoque'
        verbose_name_plural = 'Itens de estoque'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(consumption_factor__gt=0),
                name='hair_stock_consumption_factor_positive',
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.quantity_on_hand} {self.unit})"

    @property
    def service_unit(self):
        return self.consumption_unit or self.unit

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.minimum_stock


class ServiceHairStock(models.Model):
    """
    Define quanto de um item de estoque de cabelo é consumido sempre que
    um determinado serviço é agendado. Configurado via admin (inline em
    Service), é a base pra debitar o estoque automaticamente.
    """
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name='hair_stock_usages', verbose_name='Serviço'
    )
    hair_stock = models.ForeignKey(
        HairStock, on_delete=models.PROTECT, related_name='service_usages', verbose_name='Item de estoque'
    )
    quantity = models.DecimalField(
        'Consumo por atendimento',
        max_digits=10,
        decimal_places=2,
        help_text="Quantidade consumida na unidade de consumo cadastrada no item.",
    )

    class Meta:
        unique_together = ('service', 'hair_stock')
        verbose_name = 'Consumo de estoque por serviço'
        verbose_name_plural = 'Consumos de estoque por serviço'

    def __str__(self):
        return (
            f"{self.service.name} consome {self.quantity} "
            f"{self.hair_stock.service_unit} de {self.hair_stock.name}"
        )


class HairMovement(models.Model):
    MOVEMENT_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]

    hair_stock = models.ForeignKey(
        HairStock, on_delete=models.PROTECT, related_name='movements', verbose_name='Item de estoque'
    )
    movement_type = models.CharField('Tipo de movimentação', max_length=10, choices=MOVEMENT_CHOICES)
    quantity = models.DecimalField('Quantidade', max_digits=10, decimal_places=6)
    unit_price_at_time = models.DecimalField(
        'Preço unitário na movimentação', max_digits=8, decimal_places=2
    )
    appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hair_movements',
        verbose_name='Agendamento',
        help_text="Preenchido quando a saída é consumo de um agendamento específico"
    )
    note = models.CharField('Observação', max_length=255, blank=True, default='')
    created_at = models.DateTimeField('Data da movimentação', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Movimentação de estoque'
        verbose_name_plural = 'Movimentações de estoque'

    def __str__(self):
        sinal = '+' if self.movement_type == 'entrada' else '-'
        return f"{self.hair_stock.name}: {sinal}{self.quantity} em {self.created_at:%d/%m/%Y %H:%M}"