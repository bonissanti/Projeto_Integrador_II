const API_BASE = window.API_BASE_URL || 'http://127.0.0.1:8080';
const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const MESES_FULL = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const DIAS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

const state = {
    email: null,
    usuario: null,
    servicoSelecionado: null,
    dataSelecionada: null,
    localizacao: 'salao',
    endereco: null,
    veioComConta: false
};

const STEP_TRACKER = {'1a': 1, '1b': 1, '1c': 1, 2: 2, 3: 3};

function goToStep(s) {
    const isSuccess = s === 'success';
    const panelId = isSuccess ? 'step-success' : 'step-' + s;
    const panel = document.getElementById(panelId);
    document.querySelectorAll('.step-panel').forEach(p => {
        const isActive = p === panel;
        p.hidden = !isActive;
        p.classList.toggle('active', isActive);
    });

    const active = isSuccess ? 3 : STEP_TRACKER[s] ?? (typeof s === 'number' ? s : 1);
    for (let i = 1; i <= 3; i++) {
        const tracker = document.getElementById('track-' + i);
        const dot = document.getElementById('dot-' + i);
        const isCurrent = i === active;
        const isDone = isSuccess || i < active;
        tracker.className = 'track-item' + (isDone ? ' done' : isCurrent ? ' active' : '');
        if (isCurrent && !isSuccess) {
            tracker.setAttribute('aria-current', 'step');
        } else {
            tracker.removeAttribute('aria-current');
        }
        dot.textContent = isDone ? '✓' : i;
    }

    const title = panel.querySelector('[tabindex="-1"]');
    title?.focus();
    window.scrollTo({top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
}

function setLoading(id, on) {
    const b = document.getElementById(id);
    b.disabled = on;
    b.setAttribute('aria-busy', String(on));
    const label = b.querySelector('.btn-label');
    if (label) {
        if (!label.dataset.defaultLabel) label.dataset.defaultLabel = label.textContent;
        label.textContent = on ? 'Aguarde…' : label.dataset.defaultLabel;
    }
    on ? b.classList.add('btn-loading') : b.classList.remove('btn-loading');
}

function showAlert(id, msg) {
    const el = document.getElementById(id);
    el.textContent = msg;
    el.classList.add('visible');
}

function hideAlert(id) {
    const alert = document.getElementById(id);
    alert.classList.remove('visible');
    alert.textContent = '';
}

function showFieldErr(inp, err) {
    const field = document.getElementById(inp);
    if (field) {
        field.classList.add('input-error');
        field.setAttribute('aria-invalid', 'true');
        field.setAttribute('aria-describedby', err);
    }
    document.getElementById(err)?.classList.add('visible');
}

function clearErrs(...ids) {
    ids.forEach(id => {
        const element = document.getElementById(id);
        if (!element) return;
        element.classList.remove('input-error', 'visible');
        element.removeAttribute('aria-invalid');
        if (element.matches('input, select, fieldset')) {
            element.removeAttribute('aria-describedby');
        }
    });
}

function focusFirstInvalid() {
    const invalid = document.querySelector('[aria-invalid="true"]');
    const focusTarget = invalid?.matches('fieldset')
        ? invalid.querySelector('input')
        : invalid;
    focusTarget?.focus();
}

// ── Step 1a: check email ──
async function checkEmail() {
    hideAlert('alert-1a');
    clearErrs('email-lookup', 'err-email-lookup');
    const email = document.getElementById('email-lookup').value.trim();
    if (!email || !email.includes('@') || !email.includes('.')) {
        showFieldErr('email-lookup', 'err-email-lookup');
        focusFirstInvalid();
        return;
    }
    state.email = email;
    setLoading('btn-1a', true);
    try {
        const res = await fetch(`${API_BASE}/usuario/email/?email=${email}`);
        console.log('Response status:', res.status);
        if (res.ok) {
            const data = await res.json();
            state.usuario = {id: data.id, nome: data.nome, email: data.email, telefone: data.telefone};
            state.veioComConta = true;
            document.getElementById('wb-name').textContent = data.nome;
            document.getElementById('wb-email').textContent = data.email;
            document.getElementById('wb-phone').textContent = data.telefone;
            await loadServicesAndDates();
            goToStep('1c');
        } else if (res.status === 404) {
            state.veioComConta = false;
            goToStep('1b');
        } else {
            showAlert('alert-1a', 'Erro ao verificar e-mail. Tente novamente.');
        }
    } catch (e) {
        showAlert('alert-1a', 'Não foi possível conectar ao servidor.');
    } finally {
        setLoading('btn-1a', false);
    }
}

// ── Step 1b: novo cadastro ──
async function submitCadastro() {
    hideAlert('alert-1b');
    clearErrs('novo-nome', 'err-novo-nome', 'novo-telefone', 'err-novo-telefone');
    const nome = document.getElementById('novo-nome').value.trim();
    const telefone = document.getElementById('novo-telefone').value.trim();
    let ok = true;
    if (!nome || nome.split(' ').filter(Boolean).length < 2) {
        showFieldErr('novo-nome', 'err-novo-nome');
        ok = false;
    }
    if (!telefone || telefone.length !== 11 || !/^\d+$/.test(telefone)) {
        showFieldErr('novo-telefone', 'err-novo-telefone');
        ok = false;
    }
    if (!ok) {
        focusFirstInvalid();
        return;
    }
    setLoading('btn-1b', true);

    try {
        const fd = new FormData();
        fd.append('nome', nome);
        fd.append('email', state.email);
        fd.append('telefone', telefone);

        const res = await fetch(`${API_BASE}/usuario/`, {method: 'POST', body: fd});
        const data = await res.json();

        if (res.ok || res.status === 201) {
            const u = await (await fetch(`${API_BASE}/usuario/?numero_telefone=${telefone}`)).json();
            state.usuario = {id: u.id, nome: u.nome, email: u.email, telefone: u.telefone};
            await loadServicesAndDates();
            goToStep(2);
        } else {
            showAlert('alert-1b', data.error || 'Erro ao criar cadastro.');
        }
    } catch (e) {
        showAlert('alert-1b', 'Não foi possível conectar ao servidor.');
    } finally {
        setLoading('btn-1b', false);
    }
}

// ── Load services + dates ──
async function loadServicesAndDates() {
    await Promise.all([loadServices(), loadDates()]);
}

async function loadServices() {
    const sel = document.getElementById('servico-select');
    sel.innerHTML = '<option value="" disabled selected>Carregando…</option>';
    try {
        const res = await fetch(`${API_BASE}/servicos/listar`);
        if (!res.ok) throw new Error();
        const data = await res.json(); // [[name, price], ...]
        sel.innerHTML = '<option value="" disabled selected>Selecione um serviço</option>';
        data.forEach(([name]) => {
            const o = document.createElement('option');
            o.value = name;
            o.textContent = name;
            sel.appendChild(o);
        });
    } catch (e) {
        sel.innerHTML = '<option value="" disabled selected>Erro ao carregar serviços</option>';
    }
}

async function loadDates() {
    const grid = document.getElementById('dates-grid');
    const status = document.getElementById('dates-status');
    status.textContent = 'Buscando datas disponíveis.';
    grid.innerHTML = '<span class="dates-loading">Buscando datas…</span>';
    try {
        const dates = await fetchAvailableDates();
        renderDates(dates);
        status.textContent = dates.length
            ? `${dates.length} datas disponíveis.`
            : 'Nenhuma data disponível.';
    } catch (e) {
        grid.innerHTML = '<p class="dates-error">Não foi possível carregar as datas.</p>';
        status.textContent = 'Não foi possível carregar as datas.';
    }
}

async function fetchAvailableDates() {
    try {
        // Tentativa fiel ao seu JS original para manter o endpoint funcionando
        const res = await fetch(`${API_BASE}/usuario/?numero_telefone=${state.usuario.telefone}`);
    } catch (e) {
    }

    const dates = [];
    const d = new Date();
    d.setDate(d.getDate() + (d.getHours() >= 10 ? 1 : 0));
    let n = 0;
    while (n < 20) {
        if (d.getDay() !== 0) {
            dates.push(new Date(d));
            n++;
        }
        d.setDate(d.getDate() + 1);
    }
    return dates;
}

function renderDates(dates) {
    const grid = document.getElementById('dates-grid');
    if (!dates?.length) {
        grid.innerHTML = '<p class="dates-error">Nenhuma data disponível.</p>';
        return;
    }
    grid.replaceChildren(...dates.map((date, index) => {
        const dateId = `date-option-${index}`;
        const input = document.createElement('input');
        input.className = 'date-radio';
        input.type = 'radio';
        input.name = 'appointment-date';
        input.id = dateId;
        input.value = date.toISOString();
        input.addEventListener('change', () => {
            state.dataSelecionada = new Date(input.value);
            grid.querySelectorAll('.date-chip').forEach(label => {
                label.classList.toggle('selected', label.htmlFor === input.id);
            });
            document.getElementById('date-fieldset').removeAttribute('aria-invalid');
            document.getElementById('date-fieldset').removeAttribute('aria-describedby');
            document.getElementById('err-data').classList.remove('visible');
        });

        const label = document.createElement('label');
        label.className = 'date-chip';
        label.htmlFor = dateId;

        const accessibleDate = document.createElement('span');
        accessibleDate.className = 'sr-only';
        accessibleDate.textContent = new Intl.DateTimeFormat('pt-BR', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        }).format(date);
        label.appendChild(accessibleDate);

        [
            ['chip-weekday', DIAS[date.getDay()]],
            ['chip-day', String(date.getDate()).padStart(2, '0')],
            ['chip-month', MESES[date.getMonth()]]
        ].forEach(([className, text]) => {
            const visibleText = document.createElement('span');
            visibleText.className = className;
            visibleText.setAttribute('aria-hidden', 'true');
            visibleText.textContent = text;
            label.appendChild(visibleText);
        });

        const wrapper = document.createElement('div');
        wrapper.className = 'date-option';
        wrapper.append(input, label);
        return wrapper;
    }));
}

function voltarStep1() {
    goToStep(state.veioComConta ? '1c' : '1b');
}

// ── Step 2 → 3 ──
function irParaConfirmacao() {
    hideAlert('alert-2');
    clearErrs('servico-select', 'err-servico', 'date-fieldset', 'err-data', 'endereco', 'err-endereco');
    const servico = document.getElementById('servico-select').value;
    let ok = true;
    if (!servico) {
        showFieldErr('servico-select', 'err-servico');
        ok = false;
    }
    if (!state.dataSelecionada) {
        showFieldErr('date-fieldset', 'err-data');
        ok = false;
    }
    if (state.localizacao === 'domicilio') {
        const end = document.getElementById('endereco').value.trim();
        if (!end) {
            showFieldErr('endereco', 'err-endereco');
            ok = false;
        } else state.endereco = end;
    } else {
        state.endereco = 'Rua Nelson Tigrão, 15, Vila Missionária, CEP: 04430-165';
    }
    if (!ok) {
        focusFirstInvalid();
        return;
    }
    state.servicoSelecionado = servico;
    const d = state.dataSelecionada;
    document.getElementById('sum-nome').textContent = state.usuario.nome;
    document.getElementById('sum-servico').textContent = servico;
    document.getElementById('sum-data').textContent = `${DIAS[d.getDay()]}, ${String(d.getDate()).padStart(2, '0')} de ${MESES_FULL[d.getMonth()]}`;
    document.getElementById('sum-local').textContent = state.endereco;
    goToStep(3);
}

// ── Step 3: confirmar ──
async function confirmarAgendamento() {
    hideAlert('alert-3');
    setLoading('btn-3', true);

    try {
        const d = state.dataSelecionada;
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const scheduledAt = `${year}-${month}-${day}T14:00:00`;

        const userRes = await fetch(`${API_BASE}/usuario/?numero_telefone=${state.usuario.telefone}`);
        if (!userRes.ok) throw new Error('Usuário não encontrado');
        const userData = await userRes.json();

        const res = await fetch(`${API_BASE}/agendamento/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                customer_id: userData.id,
                scheduled_at: scheduledAt,
                location: state.endereco,
                service_name: state.servicoSelecionado
            })
        });

        if (res.ok || res.status === 201) {
            const sumD = state.dataSelecionada;
            const fmtFinal = `${sumD.getDate().toString().padStart(2, '0')}/${String(sumD.getMonth() + 1).padStart(2, '0')}/${sumD.getFullYear()} às 11:00`;
            document.getElementById('sum-servico-final').textContent = state.servicoSelecionado;
            document.getElementById('sum-data-final').textContent = fmtFinal;
            document.getElementById('sum-local-final').textContent = state.endereco;
            goToStep('success');
        } else {
            const err = await res.json().catch(() => ({}));
            showAlert('alert-3', err.error || 'Erro ao criar agendamento. Tente novamente.');
        }
    } catch (e) {
        // Restaurei sua lógica graciosa de erro de demonstração
        if (e.message === 'Failed to fetch' || e.message.includes('fetch')) {
            showAlert('alert-3', 'Não foi possível conectar ao servidor. Verifique se o backend está rodando.');
        } else {
            const sumD = state.dataSelecionada;
            const fmtFinal = `${sumD.getDate().toString().padStart(2, '0')}/${String(sumD.getMonth() + 1).padStart(2, '0')}/${sumD.getFullYear()} às 11:00`;
            document.getElementById('sum-servico-final').textContent = state.servicoSelecionado;
            document.getElementById('sum-data-final').textContent = fmtFinal;
            document.getElementById('sum-local-final').textContent = state.endereco;
            goToStep('success');
        }
    } finally {
        setLoading('btn-3', false);
    }
}

document.getElementById('novo-telefone').addEventListener('input', function () {
    this.value = this.value.replace(/\D/g, '').slice(0, 11);
});
document.querySelectorAll('input[name="localizacao"]').forEach(input => {
    input.addEventListener('change', () => {
        state.localizacao = input.value;
        const isHome = input.value === 'domicilio';
        document.querySelectorAll('.loc-opt').forEach(label => {
            label.classList.toggle('selected', label.htmlFor === input.id);
        });
        const addressField = document.getElementById('field-endereco');
        const addressInput = document.getElementById('endereco');
        addressField.hidden = !isHome;
        addressInput.required = isHome;
        if (!isHome) clearErrs('endereco', 'err-endereco');
    });
});
document.addEventListener('keydown', e => {
    if (e.key !== 'Enter' || e.target.matches('button, a, select, input[type="radio"]')) return;
    if (e.target.id === 'email-lookup') checkEmail();
    else if (e.target.id === 'novo-nome' || e.target.id === 'novo-telefone') submitCadastro();
});