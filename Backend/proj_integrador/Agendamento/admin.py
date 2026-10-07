from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.utils import timezone
from django.utils.html import format_html

from .models import Appointment, AppointmentxService, Customer, Service, HairStock, HairMovement, ServiceHairStock


class AppointmentxServiceInline(admin.TabularInline):
    model = AppointmentxService
    extra = 1
    autocomplete_fields = ['service']
    verbose_name = "Serviço"
    verbose_name_plural = "Serviços aplicados"


class AppointmentAdminForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = '__all__'
        widgets = {
            'scheduled_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['scheduled_at'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean_scheduled_at(self):
        data = self.cleaned_data['scheduled_at']
        criando = self.instance.pk is None
        status_novo = self.cleaned_data.get('status', 'scheduled')
        if criando and status_novo == 'scheduled' and data < timezone.now():
            raise ValidationError("Não é possível criar agendamento para uma data no passado.")
        return data


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'deleted')
    list_filter = ('deleted',)
    search_fields = ('name', 'phone', 'email')
    fields = ('name', 'email', 'phone', 'deleted')
    ordering = ('name',)

    def get_queryset(self, request):
        return Customer.active_objects.all()


class ServiceHairStockInline(admin.TabularInline):
    model = ServiceHairStock
    extra = 1
    autocomplete_fields = ['hair_stock']
    verbose_name = "Consumo de cabelo"
    verbose_name_plural = "Consumo de cabelo por agendamento"


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_formatado', 'duration')
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [ServiceHairStockInline]

    @admin.display(description='Preço', ordering='price')
    def price_formatado(self, obj):
        return f"R$ {obj.price:.2f}".replace('.', ',')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    form = AppointmentAdminForm
    list_display = (
        'customer',
        'scheduled_at',
        'status_badge',
        'location',
        'google_sync_icon',
    )
    list_filter = ('status', 'scheduled_at')
    search_fields = ('customer__name', 'customer__phone')
    date_hierarchy = 'scheduled_at'
    autocomplete_fields = ['customer']
    readonly_fields = ('google_event_id',)
    inlines = [AppointmentxServiceInline]
    actions = ['cancelar_agendamentos', 'marcar_como_concluidos']
    fieldsets = (
        (None, {
            'fields': ('customer', 'scheduled_at', 'status', 'location'),
        }),
        ('Integração Google Calendar', {
            'classes': ('collapse',),
            'fields': ('google_event_id',),
        }),
    )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        cores = {
            'scheduled': ('#0ea5e9', 'Agendado'),
            'completed': ('#16a34a', 'Concluído'),
            'canceled': ('#dc2626', 'Cancelado'),
        }
        cor, label = cores.get(obj.status, ('#6b7280', obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;">{}</span>',
            cor, label,
        )

    @admin.display(description='Google', boolean=True)
    def google_sync_icon(self, obj):
        return bool(obj.google_event_id)

    @admin.action(description='Cancelar agendamentos selecionados')
    def cancelar_agendamentos(self, request, queryset):
        atualizados = 0
        for agendamento in queryset.exclude(status='canceled'):
            agendamento.status = 'canceled'
            agendamento.save(update_fields=['status'])
            atualizados += 1
        self.message_user(request, f'{atualizados} agendamento(s) cancelado(s).')

    @admin.action(description='Marcar como concluídos')
    def marcar_como_concluidos(self, request, queryset):
        atualizados = queryset.update(status='completed')
        self.message_user(request, f'{atualizados} agendamento(s) concluído(s).')


class MovimentarEstoqueForm(forms.Form):
    quantity = forms.DecimalField(label='Quantidade', min_value=0.01, max_digits=10, decimal_places=2)
    note = forms.CharField(label='Observação', required=False, max_length=255)


@admin.register(HairStock)
class HairStockAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity_on_hand', 'unit', 'unit_price', 'minimum_stock', 'low_stock_flag', 'deleted')
    list_filter = ('deleted',)
    search_fields = ('name',)
    ordering = ('name',)
    actions = ['registrar_entrada_action', 'registrar_saida_action', 'soft_delete_action']

    # quantity_on_hand nunca é editável diretamente no form — só muda via
    # as actions abaixo, que passam pelo HairStockManager e preservam o
    # histórico em HairMovement.
    readonly_fields = ('quantity_on_hand',)
    fields = ('name', 'unit', 'unit_price', 'quantity_on_hand', 'minimum_stock', 'deleted')

    def get_queryset(self, request):
        return HairStock.active_objects.all()

    @admin.display(description='Estoque baixo', boolean=True)
    def low_stock_flag(self, obj):
        return obj.is_low_stock

    @admin.action(description='Registrar entrada (repor estoque) do item selecionado')
    def registrar_entrada_action(self, request, queryset):
        return self._movimentar_via_intermediate(request, queryset, 'entrada')

    @admin.action(description='Registrar saída (consumo) do item selecionado')
    def registrar_saida_action(self, request, queryset):
        return self._movimentar_via_intermediate(request, queryset, 'saida')

    @admin.action(description='Remover (soft delete) itens selecionados')
    def soft_delete_action(self, request, queryset):
        atualizados = queryset.update(deleted=True)
        self.message_user(request, f'{atualizados} item(ns) removido(s).')

    def _movimentar_via_intermediate(self, request, queryset, tipo):
        """
        Actions do Django Admin não têm UI nativa pra pedir um valor extra
        por item selecionado, então essa action assume uso em UM item por
        vez. Pra lançar entrada/saída em vários itens ao mesmo tempo, use
        a tela /estoque/ (API) em vez do Admin.
        """
        if queryset.count() != 1:
            self.message_user(
                request,
                'Selecione exatamente 1 item por vez para registrar entrada/saída pelo Admin.',
                messages.ERROR,
            )
            return

        hair_stock = queryset.first()

        if 'apply' in request.POST:
            form = MovimentarEstoqueForm(request.POST)
            if form.is_valid():
                quantity = form.cleaned_data['quantity']
                note = form.cleaned_data['note']
                try:
                    if tipo == 'entrada':
                        HairStock.objects.registrar_entrada(hair_stock.id, quantity, note=note)
                    else:
                        HairStock.objects.registrar_saida(hair_stock.id, quantity, note=note)
                    self.message_user(
                        request, f'{tipo.capitalize()} de {quantity} registrada para "{hair_stock.name}".',
                    )
                except ValidationError as e:
                    self.message_user(request, str(e), messages.ERROR)
                return

        form = MovimentarEstoqueForm()
        return render(request, 'admin/hair_stock_movimentar.html', {
            'hair_stock': hair_stock,
            'tipo': tipo,
            'form': form,
            'action': 'registrar_entrada_action' if tipo == 'entrada' else 'registrar_saida_action',
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            'opts': self.model._meta,
        })


@admin.register(HairMovement)
class HairMovementAdmin(admin.ModelAdmin):
    # Histórico é somente leitura — nunca editado após criado. Corrigir um
    # erro = lançar uma movimentação de ajuste, não editar o passado.
    list_display = ('hair_stock', 'movement_type', 'quantity', 'unit_price_at_time', 'appointment', 'created_at')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('hair_stock__name', 'note')
    readonly_fields = [f.name for f in HairMovement._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.site_header = "Agenda Trancista — Administração"
admin.site.site_title = "Agenda Trancista"
admin.site.index_title = "Painel de controle"