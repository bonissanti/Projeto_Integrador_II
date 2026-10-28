from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from Agendamento.models import Appointment, Customer, HairMovement, HairStock, Service


class TestesDoAdmin(TestCase):
    def criar_superusuario(self):
        usuario = get_user_model().objects.create_superuser(
            username="admin-teste",
            email="admin@example.com",
            password="senha-teste",
        )
        self.client.force_login(usuario)

    def test_model_admin_usa_unfold(self):
        for model in (Appointment, Customer, HairMovement, HairStock, Service):
            with self.subTest(model=model.__name__):
                self.assertIsInstance(admin.site._registry[model], UnfoldModelAdmin)

    def test_tela_de_login_esta_em_portugues(self):
        response = self.client.get("/admin/login/")

        self.assertContains(response, "Acesse seu painel administrativo")
        self.assertContains(response, "Voltar ao site")
        self.assertContains(response, 'name="next" value="/admin/"')

    def test_login_redireciona_para_o_admin(self):
        senha = "senha-de-teste-segura"
        get_user_model().objects.create_superuser(
            username="admin-redirecionamento",
            email="admin-redirecionamento@example.com",
            password=senha,
        )

        response = self.client.post(
            "/admin/login/",
            {
                "username": "admin-redirecionamento",
                "password": senha,
                "next": "/admin/",
            },
        )

        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_superusuario_abre_admin_e_listas_existentes(self):
        self.criar_superusuario()

        paths = (
            "/admin/",
            "/admin/Agendamento/appointment/",
            "/admin/Agendamento/customer/",
            "/admin/Agendamento/service/",
            "/admin/Agendamento/hairstock/",
            "/admin/Agendamento/hairmovement/",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_navegacao_e_rotulos_do_estoque_estao_em_portugues(self):
        self.criar_superusuario()
        HairStock.objects.create(
            name="Estoque de teste",
            unit_price=1,
            quantity_on_hand=5,
            minimum_stock=2,
        )

        dashboard = self.client.get("/admin/")
        stock_list = self.client.get("/admin/Agendamento/hairstock/")

        for label in ("Visão geral", "Agendamentos", "Clientes", "Serviços", "Estoque"):
            with self.subTest(label=label):
                self.assertContains(dashboard, label)
        self.assertContains(dashboard, "Buscar aplicativos e modelos...")
        for path, label in (
            ("/admin/Agendamento/appointment/", "Agendamentos"),
            ("/admin/Agendamento/customer/", "Clientes"),
            ("/admin/Agendamento/service/", "Serviços"),
            ("/admin/Agendamento/hairmovement/", "Movimentações de estoque"),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(
                    str(response.context["cl"].opts.verbose_name_plural),
                    label,
                )
                self.assertContains(response, label)
        self.assertEqual(
            str(stock_list.context["cl"].opts.verbose_name_plural),
            "Itens de estoque",
        )
        self.assertEqual(stock_list.context["stock_overview"], {
            "total": 1,
            "normal": 1,
            "low": 0,
            "out": 0,
        })
        self.assertContains(stock_list, "Itens de estoque")
        self.assertContains(stock_list, "Quantidade disponível")
        self.assertContains(stock_list, "Importar planilha")
        self.assertContains(stock_list, "Produtos ativos")
        self.assertContains(stock_list, "Normal")
        self.assertContains(stock_list, "stock_list.css")

    def test_lista_de_estoque_filtra_por_situacao(self):
        self.criar_superusuario()
        HairStock.objects.create(name="Normal", unit_price=1, quantity_on_hand=5, minimum_stock=2)
        HairStock.objects.create(name="Baixo", unit_price=1, quantity_on_hand=1, minimum_stock=2)
        HairStock.objects.create(name="Esgotado", unit_price=1, quantity_on_hand=0, minimum_stock=2)

        for situacao, expected_name in (
            ("normal", "Normal"),
            ("baixo", "Baixo"),
            ("esgotado", "Esgotado"),
        ):
            with self.subTest(situacao=situacao):
                response = self.client.get(
                    "/admin/Agendamento/hairstock/",
                    {"situacao": situacao},
                )
                self.assertEqual(response.context["cl"].result_count, 1)
                self.assertContains(response, expected_name)

    def test_formulario_de_estoque_tem_um_salvar_e_cancelar_para_o_inicio(self):
        self.criar_superusuario()

        response = self.client.get("/admin/Agendamento/hairstock/add/")

        self.assertContains(response, 'name="_save"')
        self.assertEqual(response.content.count(b'name="_save"'), 1)
        self.assertNotContains(response, 'name="_continue"')
        self.assertNotContains(response, 'name="_addanother"')
        self.assertContains(response, 'href="/admin/"')
        self.assertContains(response, "Cancelar")

    def test_painel_mostra_indicadores_de_agenda_e_estoque(self):
        self.criar_superusuario()
        cliente = Customer.objects.create(
            name="Cliente do painel",
            email="painel@example.com",
            phone="11999990000",
        )
        agora = timezone.now()
        Appointment.objects.bulk_create([
            Appointment(customer=cliente, scheduled_at=agora, status="scheduled"),
            Appointment(
                customer=cliente,
                scheduled_at=agora + timedelta(days=1),
                status="scheduled",
            ),
            Appointment(customer=cliente, scheduled_at=agora, status="canceled"),
        ])
        HairStock.objects.create(
            name="Estoque baixo",
            unit_price=1,
            quantity_on_hand=2,
            minimum_stock=3,
        )
        HairStock.objects.create(
            name="Estoque esgotado",
            unit_price=1,
            quantity_on_hand=0,
            minimum_stock=3,
        )
        HairStock.objects.create(
            name="Estoque negativo",
            unit_price=1,
            quantity_on_hand=-1,
            minimum_stock=3,
        )
        HairStock.objects.create(
            name="Estoque normal",
            unit_price=1,
            quantity_on_hand=5,
            minimum_stock=3,
        )
        HairStock.objects.create(
            name="Estoque baixo excluído",
            unit_price=1,
            quantity_on_hand=1,
            minimum_stock=3,
            deleted=True,
        )

        response = self.client.get("/admin/")

        indicadores = {
            indicador["label"]: indicador["value"]
            for indicador in response.context["dashboard_stats"]
        }
        self.assertEqual(indicadores["Agendamentos de hoje"], 1)
        self.assertEqual(indicadores["Próximos agendamentos"], 1)
        self.assertEqual(indicadores["Itens com estoque baixo"], 1)
        self.assertEqual(indicadores["Itens esgotados"], 1)
        self.assertEqual(indicadores["Saldos negativos"], 1)
        self.assertEqual(
            [item.name for item in response.context["low_stock_items"]],
            ["Estoque baixo"],
        )
        self.assertEqual(
            [item.customer.name for item in response.context["upcoming_appointments"]],
            ["Cliente do painel"],
        )
        self.assertContains(response, "Cliente do painel")
        self.assertContains(response, "Estoque baixo")
        self.assertContains(response, "Produtos ativos")
        self.assertContains(response, "Alertas de estoque")
        self.assertContains(response, "Últimas movimentações de estoque")
        self.assertContains(response, "Ações rápidas")

    def test_funcionario_sem_permissao_nao_ve_dados_do_painel(self):
        get_user_model().objects.create_user(
            username="funcionario",
            email="funcionario@example.com",
            password="senha-teste",
            is_staff=True,
        )
        self.client.login(username="funcionario", password="senha-teste")

        painel = self.client.get("/admin/")
        response = self.client.get("/admin/Agendamento/hairstock/")

        self.assertEqual(painel.context["dashboard_stats"], [])
        self.assertEqual(response.status_code, 403)
