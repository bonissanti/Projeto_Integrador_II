from decimal import Decimal

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import F
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Appointment, AppointmentxService, Customer, Service, HairStock, HairMovement, ServiceHairStock
from .stock_import import StockWorkbookError, import_stock_items, parse_stock_workbook


def dashboard_callback(request, context):
    estatisticas = []
    agendamentos_futuros = Appointment.objects.none()
    itens_estoque_baixo = HairStock.objects.none()
    itens_com_alerta = HairStock.objects.none()
    movimentacoes_recentes = HairMovement.objects.none()
    atalhos = []
    pode_ver_agendamentos = request.user.has_perm("Agendamento.view_appointment")
    pode_ver_estoque = request.user.has_perm("Agendamento.view_hairstock")
    pode_ver_movimentacoes = request.user.has_perm("Agendamento.view_hairmovement")

    if pode_ver_agendamentos:
        hoje = timezone.localdate()
        agendamentos_futuros = (
            Appointment.objects.filter(status="scheduled", scheduled_at__gte=timezone.now())
            .select_related("customer")
            .prefetch_related("appointmentxservice_set__service")
            .order_by("scheduled_at")
        )
        estatisticas.extend([
            {
                "label": "Agendamentos de hoje",
                "value": Appointment.objects.filter(
                    status="scheduled",
                    scheduled_at__date=hoje,
                ).count(),
                "url": reverse("admin:Agendamento_appointment_changelist"),
                "link_label": "Ver agenda",
                "featured": True,
            },
            {
                "label": "Próximos agendamentos",
                "value": agendamentos_futuros.count(),
                "url": reverse("admin:Agendamento_appointment_changelist"),
                "link_label": "Ver agenda",
                "featured": False,
            },
        ])
        if request.user.has_perm("Agendamento.add_appointment"):
            atalhos.append({
                "label": "Novo agendamento",
                "url": reverse("admin:Agendamento_appointment_add"),
                "icon": "event",
            })

    if request.user.has_perm("Agendamento.view_customer"):
        estatisticas.append({
            "label": "Clientes cadastrados",
            "value": Customer.active_objects.filter(deleted=False).count(),
            "url": reverse("admin:Agendamento_customer_changelist"),
            "link_label": "Ver clientes",
            "featured": True,
        })
        if request.user.has_perm("Agendamento.add_customer"):
            atalhos.append({
                "label": "Novo cliente",
                "url": reverse("admin:Agendamento_customer_add"),
                "icon": "person_add",
            })

    if request.user.has_perm("Agendamento.view_service"):
        atalhos.append({
            "label": "Configurar consumo",
            "url": reverse("admin:Agendamento_service_changelist"),
            "icon": "water_drop",
        })
        if request.user.has_perm("Agendamento.add_service"):
            atalhos.append({
                "label": "Novo serviço",
                "url": reverse("admin:Agendamento_service_add"),
                "icon": "content_cut",
            })

    if pode_ver_estoque:
        estoque_ativo = HairStock.objects.listar_ativos()
        estoque_baixo = estoque_ativo.filter(
            quantity_on_hand__gt=0,
            quantity_on_hand__lte=F("minimum_stock"),
        )
        itens_estoque_baixo = estoque_baixo.order_by("quantity_on_hand", "name")[:5]
        itens_com_alerta = estoque_ativo.filter(
            quantity_on_hand__gte=0,
            quantity_on_hand__lte=F("minimum_stock"),
        ).order_by("quantity_on_hand", "name")[:5]
        estatisticas.extend([
            {
                "label": "Produtos ativos",
                "value": estoque_ativo.count(),
                "url": reverse("admin:Agendamento_hairstock_changelist"),
                "link_label": "Ver estoque",
                "featured": True,
            },
            {
                "label": "Itens com estoque baixo",
                "value": estoque_baixo.count(),
                "url": reverse("admin:Agendamento_hairstock_changelist"),
                "link_label": "Ver estoque",
                "featured": True,
            },
            {
                "label": "Itens esgotados",
                "value": estoque_ativo.filter(quantity_on_hand=0).count(),
                "url": reverse("admin:Agendamento_hairstock_changelist"),
                "link_label": "Ver estoque",
                "featured": True,
            },
            {
                "label": "Saldos negativos",
                "value": estoque_ativo.filter(quantity_on_hand__lt=0).count(),
                "url": reverse("admin:Agendamento_hairstock_changelist"),
                "link_label": "Ver estoque",
                "featured": False,
            },
        ])
        if request.user.has_perm("Agendamento.add_hairstock"):
            atalhos.append({
                "label": "Novo produto",
                "url": reverse("admin:Agendamento_hairstock_add"),
                "icon": "inventory_2",
            })
            atalhos.append({
                "label": "Importar planilha",
                "url": reverse("admin:Agendamento_hairstock_importar"),
                "icon": "upload",
            })

    if pode_ver_movimentacoes:
        movimentacoes_recentes = (
            HairMovement.objects.select_related("hair_stock", "appointment")
            .order_by("-created_at")[:5]
        )

    context.update({
        "dashboard_stats": estatisticas,
        "upcoming_appointments": agendamentos_futuros[:5],
        "low_stock_items": itens_estoque_baixo,
        "stock_alert_items": itens_com_alerta,
        "recent_stock_movements": movimentacoes_recentes,
        "quick_actions": atalhos,
        "can_view_appointments": pode_ver_agendamentos,
        "can_view_stock": pode_ver_estoque,
        "can_view_movements": pode_ver_movimentacoes,
    })
    return context


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
class CustomerAdmin(ModelAdmin):
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
    verbose_name = "Consumo de estoque"
    verbose_name_plural = "Consumo de estoque por serviço"


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = ('name', 'price_formatado', 'duration')
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [ServiceHairStockInline]

    @admin.display(description='Preço', ordering='price')
    def price_formatado(self, obj):
        return f"R$ {obj.price:.2f}".replace('.', ',')


@admin.register(Appointment)
class AppointmentAdmin(ModelAdmin):
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


class SituacaoEstoqueFilter(admin.SimpleListFilter):
    title = 'situação do estoque'
    parameter_name = 'situacao'

    def lookups(self, request, model_admin):
        return (
            ('normal', 'Normal'),
            ('baixo', 'Estoque baixo'),
            ('esgotado', 'Esgotado'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'normal':
            return queryset.filter(quantity_on_hand__gt=F('minimum_stock'))
        if self.value() == 'baixo':
            return queryset.filter(
                quantity_on_hand__gt=0,
                quantity_on_hand__lte=F('minimum_stock'),
            )
        if self.value() == 'esgotado':
            return queryset.filter(quantity_on_hand__lte=0)
        return queryset


@admin.register(HairStock)
class HairStockAdmin(ModelAdmin):
    change_list_template = 'admin/Agendamento/hairstock/change_list.html'
    list_before_template = 'admin/Agendamento/hairstock/stock_summary.html'
    import_template = 'admin/Agendamento/hairstock/import.html'
    import_session_key = 'hair_stock_import_preview'
    max_import_size = 5 * 1024 * 1024
    list_display = (
        'name',
        'quantity_on_hand',
        'unit',
        'consumption_conversion',
        'unit_price',
        'minimum_stock',
        'stock_status',
    )
    list_filter = ('deleted', SituacaoEstoqueFilter)
    search_fields = ('name',)
    ordering = ('name',)
    actions = ['registrar_entrada_action', 'registrar_saida_action', 'soft_delete_action']

    # quantity_on_hand nunca é editável diretamente no form — só muda via
    # as actions abaixo, que passam pelo HairStockManager e preservam o
    # histórico em HairMovement.
    readonly_fields = ('quantity_on_hand',)
    fields = (
        'name',
        'unit',
        'consumption_unit',
        'consumption_factor',
        'unit_price',
        'quantity_on_hand',
        'minimum_stock',
        'deleted',
    )

    def get_queryset(self, request):
        return HairStock.active_objects.all()

    def changelist_view(self, request, extra_context=None):
        queryset = HairStock.objects.listar_ativos()
        extra_context = {
            **(extra_context or {}),
            'stock_overview': {
                'total': queryset.count(),
                'normal': queryset.filter(
                    quantity_on_hand__gt=F('minimum_stock')
                ).count(),
                'low': queryset.filter(
                    quantity_on_hand__gt=0,
                    quantity_on_hand__lte=F('minimum_stock'),
                ).count(),
                'out': queryset.filter(quantity_on_hand__lte=0).count(),
            },
        }
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        custom_urls = [
            path(
                'importar/',
                self.admin_site.admin_view(self.importar_planilha),
                name='Agendamento_hairstock_importar',
            ),
        ]
        return custom_urls + super().get_urls()

    def importar_planilha(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied

        session_key = f'{self.import_session_key}_{request.user.pk}'
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'upload':
                request.session.pop(session_key, None)
                uploaded_file = request.FILES.get('arquivo')
                if uploaded_file is None:
                    messages.error(request, 'Selecione uma planilha .xlsx para importar.')
                    return self._render_import_page(request)
                if not uploaded_file.name.lower().endswith('.xlsx'):
                    messages.error(request, 'O arquivo precisa estar no formato .xlsx.')
                    return self._render_import_page(request)
                if uploaded_file.size > self.max_import_size:
                    messages.error(request, 'A planilha não pode exceder 5 MB.')
                    return self._render_import_page(request)

                try:
                    workbook_data = parse_stock_workbook(uploaded_file)
                except StockWorkbookError as error:
                    messages.error(request, str(error))
                    return self._render_import_page(request)

                request.session[session_key] = {
                    'created_at': timezone.now().timestamp(),
                    'stock_items': [
                        {
                            **item,
                            'minimum_stock': str(item['minimum_stock']),
                            'initial_quantity': str(item['initial_quantity']),
                            'unit_price': (
                                str(item['unit_price'])
                                if item['unit_price'] is not None
                                else None
                            ),
                        }
                        for item in workbook_data.stock_items
                    ],
                    'consumption_rows': [
                        {
                            **row,
                            'minimum': str(row['minimum']),
                            'average': str(row['average']),
                            'maximum': str(row['maximum']),
                        }
                        for row in workbook_data.consumption_rows
                    ],
                }
                return self._render_import_page(request)

            if action == 'confirm':
                preview = request.session.get(session_key)
                if preview is None:
                    messages.error(request, 'Envie a planilha novamente para iniciar a importação.')
                    return self._render_import_page(request)
                if timezone.now().timestamp() - preview['created_at'] > 1800:
                    request.session.pop(session_key, None)
                    messages.error(request, 'A prévia expirou. Envie a planilha novamente.')
                    return self._render_import_page(request)

                stock_items = [
                    {
                        **item,
                        'minimum_stock': Decimal(item['minimum_stock']),
                        'initial_quantity': Decimal(item['initial_quantity']),
                        'unit_price': (
                            Decimal(item['unit_price'])
                            if item['unit_price'] is not None
                            else None
                        ),
                    }
                    for item in preview['stock_items']
                ]
                confirm_zero_prices = request.POST.get('confirmar_preco_zero') == 'on'
                try:
                    result = import_stock_items(stock_items, confirm_zero_prices)
                except StockWorkbookError as error:
                    messages.error(request, str(error))
                    return self._render_import_page(request, preview)

                request.session.pop(session_key, None)
                messages.success(
                    request,
                    f"Importação concluída: {result.created_count} item(ns) adicionado(s).",
                )
                if result.skipped_names:
                    messages.warning(
                        request,
                        f"{len(result.skipped_names)} item(ns) já existente(s) foram ignorados "
                        "para preservar o saldo atual.",
                    )
                return redirect('admin:Agendamento_hairstock_changelist')

            if action == 'cancel':
                request.session.pop(session_key, None)
                return redirect('admin:index')

        return self._render_import_page(request)

    def _render_import_page(self, request, preview=None):
        if preview is None:
            preview = request.session.get(
                f'{self.import_session_key}_{request.user.pk}'
            )
        stock_items = preview['stock_items'] if preview else []
        existing_names = {
            name.casefold()
            for name in HairStock.active_objects.filter(deleted=False).values_list(
                'name', flat=True
            )
        }
        stock_items = [
            {
                **item,
                'already_exists': item['name'].casefold() in existing_names,
            }
            for item in stock_items
        ]
        missing_price_count = sum(
            item['unit_price'] is None and not item['already_exists']
            for item in stock_items
        )
        context = {
            **self.admin_site.each_context(request),
            'title': 'Importar planilha de estoque',
            'opts': self.model._meta,
            'preview': preview,
            'stock_items': stock_items,
            'existing_names': existing_names,
            'missing_price_count': missing_price_count,
            'consumption_count': len(preview['consumption_rows']) if preview else 0,
            'procedure_names': sorted({
                row['procedure'] for row in preview['consumption_rows']
            }) if preview else [],
            'changelist_url': reverse('admin:Agendamento_hairstock_changelist'),
        }
        request.current_app = self.admin_site.name
        return render(request, self.import_template, context)

    @admin.display(description='Situação', ordering='quantity_on_hand')
    def stock_status(self, obj):
        if obj.quantity_on_hand <= 0:
            label, css_class = 'Esgotado', 'stock-status--out'
        elif obj.is_low_stock:
            label, css_class = 'Estoque baixo', 'stock-status--low'
        else:
            label, css_class = 'Normal', 'stock-status--normal'
        return format_html(
            '<span class="stock-status {}">{}</span>',
            css_class,
            label,
        )

    @admin.display(description='Conversão de consumo')
    def consumption_conversion(self, obj):
        return f"1 {obj.unit} = {obj.consumption_factor} {obj.service_unit}"

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
class HairMovementAdmin(ModelAdmin):
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