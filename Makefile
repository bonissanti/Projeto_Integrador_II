SHELL := /bin/bash
VENV := .venv
MANAGE := Backend/proj_integrador/manage.py

ifeq ($(OS),Windows_NT)
PY := $(VENV)\\Scripts\\python.exe
UV_CMD := $(VENV)\\Scripts\\uv.exe
ACTIVATE_CMD := & $(VENV)\\Scripts\\Activate.ps1
RM := cmd /C rmdir /S /Q
PYTHON_BIN := python
else
PY := $(VENV)/bin/python
UV_CMD := $(VENV)/bin/uv
ACTIVATE_CMD := source $(VENV)/bin/activate
RM := rm -rf
PYTHON_BIN := $(shell command -v python3 || command -v python)
endif

.PHONY: help setup install venv activate migrate makemigrations runserver createsuperuser ensure-admin test check init-env update-requirements clean inserir-servicos

help:
	@echo ""
	@echo "Projeto Integrador I - Comandos Disponiveis"
	@echo "=============================================="
	@echo ""
	@echo "INICIAR (escolha um):"
	@echo "  make setup              Prepara tudo (cria Python isolado e instala dependências)"
	@echo "  make venv               Apenas cria a pasta '$(VENV)' com Python isolado"
	@echo "  make install            Apenas instala dependências com uv (precisa já ter 'uv')"
	@echo ""
	@echo "ATIVAR AMBIENTE:"
	@echo "  make activate           Mostra o comando para ativar o Python isolado"
	@echo "  make init-env           Cria .env com SECRET_KEY gerado (nao sobrescreve existente)"
	@echo ""
	@echo "EXECUTAR PROJETO:"
	@echo "  make migrate            Prepara o banco de dados"
	@echo "  make runserver          Inicia o servidor (acesse http://localhost:8000)"
	@echo "  make createsuperuser    Cria conta de administrador"
	@echo ""
	@echo "QUALIDADE:"
	@echo "  make test               Roda a suite de testes"
	@echo "  make check              Verifica a configuração do Django"
	@echo ""
	@echo "MANUTENÇÃO:"
	@echo "  make update-requirements Atualiza requirements.txt com uv"
	@echo "  make clean              Remove Python isolado e arquivos temporários"
	@echo ""
	@echo ""
	@echo "INSERIR SERVIÇOS:"
	@echo " make inserir-servicos   Insere o seed de serviços de tranças no banco"

venv:
	@echo "Preparando Python isolado em '$(VENV)'..."
	@$(PYTHON_BIN) -m venv $(VENV)
	@echo "Instalando uv (gerenciador de pacotes moderno)..."
	@$(PY) -m pip install --upgrade uv

install: venv
	@echo ""
	@echo "Instalando dependencias com uv..."
	@$(UV_CMD) pip install -r requirements.txt || echo "AVISO: requirements.txt nao encontrado ou vazio, pulando instalacao"

init-env:
	@if [ -f .env ]; then \
		echo "Arquivo .env ja existe. Para recriar, remova primeiro: rm .env"; \
	else \
		echo "Gerando SECRET_KEY e criando .env..."; \
		SECRET=$$($(PYTHON_BIN) -c "import secrets; print(secrets.token_urlsafe(64))"); \
		printf "SECRET_KEY=%s\nVERIFY_TOKEN=altere-aqui-o-token-do-whatsapp\n" "$$SECRET" > .env; \
		echo "Arquivo .env criado. Ajuste VERIFY_TOKEN com o token do WhatsApp Cloud API."; \
	fi

setup: install init-env migrate inserir-servicos
	@echo ""
	@echo "Configuracao concluida!"
	@echo ""
	@echo "Para ativar o ambiente, execute:"
	@echo "   make activate"
	@echo ""

activate:
	@echo "Ativando o ambiente virtual em uma nova sessao do terminal..."
ifeq ($(OS),Windows_NT)
	@cmd /k "$(VENV)\\Scripts\\activate.bat"
else
	@bash -c "source $(VENV)/bin/activate && exec bash"
endif

migrate:
	@echo "Preparando banco de dados..."
	@$(PY) $(MANAGE) migrate
	@echo "Banco pronto!"

makemigrations:
	@echo "Criando migrations..."
	@$(PY) $(MANAGE) makemigrations

ensure-admin:
	@$(PY) $(MANAGE) ensure_admin

runserver: ensure-admin
	@echo ""
	@echo "Iniciando servidor Django..."
	@echo "   Acesse: http://localhost:8000"
	@echo "   Admin dev: user=admin / senha=12345"
	@echo "   Para parar: pressione Ctrl+C"
	@echo ""
	@$(PY) $(MANAGE) runserver

createsuperuser:
	@echo ""
	@echo "Criando conta de administrador..."
	@echo "   Voce sera solicitado a digitar nome de usuario, email e senha."
	@echo ""
	@$(PY) $(MANAGE) createsuperuser
	@echo ""
	@echo "Conta criada! Acesse em: http://localhost:8000/admin"
	@echo ""

inserir-servicos:
	@echo ""
	@echo "Inserindo seed de serviços no banco..."
	@$(PY) $(MANAGE) seed_services

test:
	@echo "Rodando testes..."
	@$(PY) $(MANAGE) test Agendamento WhatsAppBot Usuario

check:
	@echo "Verificando configuração Django..."
	@$(PY) $(MANAGE) check

update-requirements:
	@echo "Atualizando requirements.txt com uv..."
	@$(UV_CMD) pip freeze > requirements.txt
	@echo "requirements.txt atualizado"

clean:
	@echo "Limpando..."
	@echo "   Removendo Python isolado 'uv'..."
	@$(RM) $(VENV) || true
	@echo "   Removendo arquivos de cache Python..."
	@$(PYTHON_BIN) -c "import os, shutil; [shutil.rmtree(os.path.join(r, d), ignore_errors=True) for r, dirs, f in os.walk('.') for d in dirs if d == '__pycache__']" || true
	@echo "Limpeza concluida"
	@echo ""
	@echo "Para recomecar, execute: make setup"
	@echo ""
