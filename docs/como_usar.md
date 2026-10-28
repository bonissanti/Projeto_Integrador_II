# Agenda Trancista — Manual do Usuário (Estoque de Cabelo)

Este guia é pra Tati (trancista) e qualquer outra pessoa não-desenvolvedora que precise usar o painel administrativo do sistema (o "Admin" do Django) pra cuidar do estoque de cabelo. Não é preciso saber programar pra seguir este manual.

## 1. Acessando o Admin

1. Acesse o endereço do site seguido de `/admin/` (ex: `https://seu-site.com/admin/`).
2. Entre com seu usuário e senha de administrador.
3. Você verá o painel com as seções: **Customers**, **Services**, **Appointments**, **Hair stocks**, **Hair movements** e **Service hair stocks**.

## 2. Conceitos básicos

O sistema controla o estoque de cabelo usado nos atendimentos através de 3 peças que trabalham juntas:

| Tabela (nome no Admin) | O que é                                                                                                                                    | Quem mexe nela e quando |
|---|--------------------------------------------------------------------------------------------------------------------------------------------|---|
| **Hair stocks** | O "estoque" em si: cada item de cabelo que você tem (ex: "cabelo"), com quantidade disponível, preço, unidade e estoque mínimo.            | Você, sempre que compra/recebe cabelo (entrada) ou precisa corrigir uma quantidade (saída manual). |
| **Service hair stocks** | A "receita" de cada serviço: quanto de um item de cabelo aquele serviço gasta por atendimento (ex: "Tranças Soltas consome 6g de cabelo"). | Você, **uma única vez por serviço** (configuração, não é por agendamento). |
| **Hair movements** | O **histórico** de tudo que entrou ou saiu do estoque — um extrato, tipo extrato bancário.                                                 | O sistema registra sozinho, automaticamente, toda vez que o estoque muda (entrada, saída manual, ou consumo de um agendamento). Você nunca edita isso na mão. |

## 3. Passo a passo: cadastrando um item de estoque de cabelo

1. No Admin, clique em **Hair stocks** → **Adicionar**.
2. Preencha:
   - **Name**: nome do item (ex: "cabelo 100g Preto").
   - **Unit**: unidade de medida (ex: `g`, `un`, `pacote`).
   - **Unit price**: preço unitário (usado só pra referência/histórico).
   - **Quantity on hand**: quantidade que você já tem (só na criação; depois disso esse campo fica travado — veja a seção 5).
   - **Minimum stock**: quantidade mínima que, quando atingida, dispara um aviso automático pra você no Telegram.
3. Salve.

### Importar o estoque inicial de uma planilha

1. No Admin, abra **Hair stocks** e clique em **Importar planilha**.
2. Envie o arquivo `.xlsx` com as abas **Estoque inicial** e **Consumo por procedimento**.
3. Confira a prévia. Itens que já existem serão ignorados e terão o saldo atual preservado.
4. Se a planilha não tiver preço unitário, marque a confirmação para importar os novos itens sem preço como **R$ 0,00**.
5. Confirme a importação. O saldo inicial será registrado também em **Hair movements**.

O arquivo precisa ter até 5 MB. A importação lê os dados de consumo para exibição, mas não os associa automaticamente aos serviços: os procedimentos da planilha precisam ser mapeados aos serviços existentes e as unidades de consumo, convertidas conforme cada produto.

### Configurar unidades de consumo diferentes

Quando o produto é comprado em uma unidade e consumido em outra, configure a conversão no item de estoque:

- **Unit**: unidade em que o estoque é comprado e controlado (ex.: `frasco`).
- **Consumption unit**: unidade usada na receita do serviço (ex.: `ml`).
- **Consumption per stock unit**: quantidade de unidades de consumo contidas em uma unidade de estoque (ex.: `200`, se 1 frasco contém 200 ml).

No exemplo, configure `frasco`, `ml` e `200`. Depois, informe o consumo por atendimento em **Services → Consumo de estoque** usando `ml`. O sistema converte o consumo para a unidade do estoque ao registrar a saída.

## 4. Passo a passo: configurando quanto cada serviço consome (uma vez só)

Isso é o que faz o débito automático funcionar. **Sem este passo, agendar um serviço não desconta nada do estoque.**

1. No Admin, clique em **Services** e abra o serviço que você quer configurar (ex: "Tranças Soltas (Individuais)").
2. Role até a seção **"Consumo de cabelo"**.
3. Clique para adicionar uma linha:
   - **Hair stock**: escolha o item de cabelo usado nesse serviço (ex: "cabelo").
   - **Quantity**: quantidade consumida **por atendimento**, na unidade de consumo do item (ex.: `30 ml`).
4. Se o serviço usa mais de um tipo de cabelo, adicione mais linhas (uma por item).
5. Salve o serviço.

Repita esse processo pra cada serviço que você oferece. É **configuração única** — depois disso, você não precisa mexer aqui de novo, a menos que mude a "receita" de um serviço (ex: passar a usar outra marca ou quantidade).

> ⚠️ Enquanto um serviço não tiver nenhuma linha de "Consumo de cabelo", agendar aquele serviço não desconta nada do estoque — é como se ele não gastasse cabelo nenhum.

## 5. Como o débito automático acontece

A partir do momento em que você configurou o "Consumo de cabelo" de um serviço (seção 4):

- Toda vez que um cliente agenda aquele serviço — seja pelo **site** ou pelo **bot do Telegram** — o sistema automaticamente desconta a quantidade configurada do **Hair stock** correspondente.
- Isso acontece no momento em que o agendamento é criado (confirmado), não precisa fazer nada manualmente.
- Cada desconto automático gera uma linha em **Hair movements**, já ligada ao agendamento que causou aquele consumo — assim você sempre consegue rastrear "por que esse estoque baixou".

## 6. Registrando entrada/saída manual de estoque

Além do débito automático dos agendamentos, você pode (e deve) registrar manualmente:

- **Entrada**: quando você compra/recebe mais cabelo (repor estoque).
- **Saída**: quando precisa tirar cabelo do estoque por outro motivo que não seja um agendamento (perda, uso interno, ajuste, etc).

Como fazer:

1. No Admin, vá em **Hair stocks**.
2. Marque a caixinha (checkbox) do item que você quer movimentar.
3. No menu **Action** (bem no topo da lista), escolha **"Registrar entrada (repor estoque) do item selecionado"** ou **"Registrar saída (consumo) do item selecionado"**.
4. Clique em **Go**.
5. Preencha a quantidade e, se quiser, uma observação (ex: "Compra no fornecedor X").
6. Confirme.

> Você só pode fazer essa ação em **1 item por vez** pelo Admin. Isso é intencional: é a forma mais segura de garantir que o histórico (Hair movements) fique certinho.

> Você **não edita diretamente** o campo "Quantity on hand" de um Hair stock — ele é só leitura no formulário. Toda mudança de quantidade (seja por agendamento, entrada ou saída manual) tem que passar pelas ações acima, justamente pra sempre deixar um registro em **Hair movements**.

## 7. Consultando o histórico (Hair movements)

A tela **Hair movements** é o extrato completo do seu estoque de cabelo. Lá você vê, para cada movimentação:

- Qual item de estoque foi afetado (`Hair stock`).
- Se foi **entrada** ou **saída**.
- A quantidade movimentada.
- O preço unitário no momento daquela movimentação (fica "congelado" ali, mesmo que você mude o preço depois).
- O **agendamento** relacionado, se a saída foi um consumo automático de atendimento (se foi uma entrada/saída manual, esse campo fica vazio).
- A data/hora exata e uma observação (se foi preenchida).

Essa tela é **somente leitura** — você não consegue editar nem apagar movimentações antigas (inclusive os botões de adicionar/editar/excluir não aparecem). Isso é proposital: o histórico precisa ser confiável. Se alguma quantidade estiver errada, o jeito certo de corrigir é lançar uma **nova** movimentação de ajuste (entrada ou saída), nunca editar o passado.

Use essa tela sempre que quiser entender "por que esse estoque está nesse número" — basta filtrar pelo item (`Hair stock`) ou pelo tipo de movimentação.

## 8. Alerta de estoque baixo

Quando a quantidade de um item (`Hair stock`) fica igual ou menor que o **Minimum stock** configurado (seja por causa de um agendamento ou de uma saída manual), o sistema te avisa automaticamente por mensagem no Telegram.

Pra esse aviso funcionar, é preciso que o administrador do sistema (quem configura o servidor) tenha definido a variável de ambiente `TELEGRAM_ADMIN_CHAT_ID` com o seu chat ID do Telegram. Se você não está recebendo os avisos, peça pra essa configuração ser verificada.

## 9. Resumo rápido (TL;DR)

1. Cadastre seus itens de cabelo em **Hair stocks**.
2. Configure, uma vez por serviço, quanto cada serviço consome em **Services → Consumo de cabelo**.
3. A partir daí, cada agendamento (site ou Telegram) desconta o estoque sozinho — você não faz nada.
4. Use as ações de **Registrar entrada/saída** em **Hair stocks** pra repor estoque ou fazer ajustes manuais.
5. Consulte **Hair movements** sempre que quiser ver o extrato completo do que entrou/saiu e por quê.
6. Fique de olho no **Telegram** — ele avisa sozinho quando algo está acabando.
