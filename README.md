# ✉️ Disparador de E-mails CP Fani

> Aplicação desktop robusta e intuitiva desenvolvida em Python para disparo personalizado e automatizado de e-mails corporativos em massa para revendedores.

---

## 📌 Índice

- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-funcionalidades)
- [Requisitos do Sistema](#-requisitos-do-sistema)
- [Instalação e Execução (Per-User)](#-instalação-e-execução-per-user)
- [Guia de Configuração SMTP](#-guia-de-configuração-smtp)
- [Como Utilizar](#-como-utilizar)
- [Boas Práticas Anti-Spam](#-boas-práticas-anti-spam)
- [Conformidade com a LGPD](#-conformidade-com-a-lgpd)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Solução de Problemas](#-solução-de-problemas)
- [Suporte](#-suporte)

---

## 🚀 Visão Geral

O **Disparador de E-mails CP Fani** foi criado para simplificar o envio de comunicados corporativos, promoções e avisos para bases de revendedores da CP Fani. A aplicação roda localmente por usuário (*per-user*), sem exigir privilégios de administrador ou dependências globais do sistema.

---

## ✨ Funcionalidades

- 📬 **Suporte Multi-Provedor:** Suporte pré-configurado para Gmail e GoDaddy com porta SSL/STARTTLS.
- 🎨 **Editor Rich Text com Imagens Inline:** Criação visual com formatação completa e anexação automática de imagens locais via CID.
- 🏷️ **Personalização Dinâmica:** Substituição automática de tags como `{{primeiro_nome}}`, `{{nome_completo}}`, `{{codigo}}` e colunas personalizadas da planilha.
- 📊 **Importação Inteligente:** Leitura de planilhas Excel (`.xlsx`) e arquivos `.csv` com auto-detecção de colunas, remoção de duplicados e higienização contra valores nulos (`NaN` / `.0`).
- 🔒 **Segurança Nativa:** Salvamento criptografado de credenciais no Cofre do Sistema Operacional (`keyring`).
- ⏱️ **Controle de Vazão Responsivo:** Ajuste de limites diários e intervalos aleatórios entre disparos com pausa/retomada instantânea.
- 📝 **Auditoria e Logs em Tempo Real:** Registro em CSV resiliente contra bloqueios de arquivos no Excel e envio automático de relatório final com anexo para a equipe de TI.

---

## 📋 Requisitos do Sistema

| Requisito | Especificação Mínima | Recomendado |
|---|---|---|
| **Ambiente Python** | Python 3.12 (64-bit) | Python 3.12 (64-bit) |
| **Sistema Operacional** | Windows 10 64-bit | Windows 11 64-bit |
| **Hardware** | Intel Core i3 / 4 GB RAM | Intel Core i5/i7 / 8 GB+ RAM |
| **Espaço em Disco** | 300 MB livre | 1 GB livre |

---

## 💻 Instalação e Execução (Per-User)

A instalação do aplicativo é realizada por usuário em `%USERPROFILE%\Documents\Disparador de e-mails` (ou em pasta sem sincronização do OneDrive para evitar bloqueio de arquivos).

### Método Automático (Recomendado)

1. Baixe os arquivos do projeto para o seu computador.
2. Dê um duplo clique no arquivo **`instalar_completo.bat`**.
   - O instalador verificará/configurará o ambiente virtual em **Python 3.12 (64-bit)**.
   - Instalará todas as dependências isoladas.
   - Criará atalhos na sua Área de Trabalho e Menu Iniciar.
3. Para iniciar a aplicação, utilize o atalho criado ou dê um duplo clique no arquivo **`executar.bat`**.

---

## ⚙️ Guia de Configuração SMTP

### 🔴 Gmail (Google Workspace ou Pessoal)

> ⚠️ **Atenção:** O Gmail exige obrigatoriamente a utilização de uma **Senha de App** para conexões SMTP externas.

1. Acesse as [Configurações de Segurança do Google](https://myaccount.google.com/security).
2. Certifique-se de que a **Verificação em Duas Etapas** está **ativada**.
3. Acesse a seção de [Senhas de App](https://myaccount.google.com/apppasswords).
4. Crie um nome para a senha de app (ex: `Disparador CP Fani`) e copie o código gerado de 16 caracteres.
5. No aplicativo, selecione o provedor `Gmail`, a porta `STARTTLS (587)` ou `SSL (465)`, e insira essa chave no campo de senha.

---

### 🔵 GoDaddy

1. Verifique os limites de disparo diário do seu plano no painel da GoDaddy.
2. No aplicativo, selecione o provedor `GoDaddy`, a porta `SSL (465)` e utilize sua senha padrão da conta de e-mail.

---

## 🕹️ Como Utilizar

+-----------------------------------------------------------------------+
|  [1] SMTP  -->  [2] Destinatários  -->  [3] Mensagem  -->  [4] Envio  |
+-----------------------------------------------------------------------+


1. **Aba "1. Configuração SMTP":** Preencha seu e-mail e senha, teste a conexão e marque a opção para lembrar credenciais com segurança.
2. **Aba "2. Destinatários":** Clique em "Selecionar Arquivo" para importar sua base (`.xlsx` ou `.csv`). Confirme o mapeamento das colunas e clique em "Processar e Validar Dados".
3. **Aba "3. Mensagem":** Escreva o assunto e o corpo da mensagem. Insira tags dinâmicas usando os botões de menu ou digitando `{{primeiro_nome}}`. Use a opção "Pré-visualizar" para conferir o resultado.
4. **Aba "4. Envio":** Ajuste o limite diário e o intervalo entre disparos (ex: 10 a 30s). Envie um e-mail de teste para a sua caixa de entrada e clique em **"▶ Iniciar"**.
5. **Aba "5. Log":** Acompanhe a tabela de registros de envio em tempo real e acesse a pasta contendo os relatórios em formato CSV.

---

## 🛡️ Boas Práticas Anti-Spam

Para garantir alta entregabilidade nas caixas de entrada dos revendedores:

### Registros DNS Recomendados
- **SPF:** `v=spf1 include:_spf.google.com ~all` (ajuste de acordo com seu provedor)
- **DMARC:** Configurado e apontado para monitoramento corporativo.

### Regra de Cadência
- Mantenha o limite diário abaixo de **200 e-mails/dia** por conta.
- Utilize um intervalo aleatório de no mínimo **10 a 30 segundos** entre cada envio.

---

## 🔒 Conformidade com a LGPD

- **Armazenamento Seguro:** As senhas SMTP são criptografadas via cofre nativo do Windows (Windows Credential Manager / `keyring`).
- **Execução Local:** Toda a leitura e processamento de planilhas ocorre exclusivamente na memória da sua máquina local.

---

## 📂 Estrutura do Projeto

Disparador-de-emails-CP-FANI/
├── main.py                   # Ponto de entrada e tratamento global de exceções
├── executar.bat              # Script de inicialização silenciosa sem console
├── instalar_completo.bat     # Instalador automático do ambiente virtual
├── requirements.txt          # Dependências do projeto Python
├── README.md                 # Documentação oficial
├── app/
│   ├── config.py             # Configurações globais e caminhos de pastas
│   ├── ui/
│   │   ├── main_window.py    # Janela principal, abas e gerenciador de eventos
│   │   ├── components.py     # Componentes visuais personalizados
│   │   └── styles.py         # Folhas de estilo da interface (QSS)
│   └── core/
│       ├── importer.py       # Importação e higienização de planilhas
│       ├── template_engine.py# Motor de substituição de variáveis e tags
│       ├── smtp_client.py    # Cliente SMTP com conexões seguras e timeout
│       ├── sender_worker.py  # Thread de disparo e controle de execução
│       ├── logger.py         # Registrador de histórico CSV e envio de relatório
│       └── updater.py        # Gerenciador de atualizações do app
├── ico/                      # Ícones da aplicação
└── logo/                     # Identidade visual CP Fani


---

## 🛠️ Solução de Problemas

<details>
<summary><b> Falha na Autenticação (Gmail)</b></summary>
Verifique se você gerou e inseriu a <b>Senha de App de 16 caracteres</b>. Senhas normais da conta do Google são bloqueadas pelo servidor SMTP.
</details>

<details>
<summary><b> Planilha com números e códigos no formato "192713.0"</b></summary>
O importador do sistema remove automaticamente a terminação `.0` de colunas numéricas e trata células vazias para evitar exibição de texto `"nan"`.
</details>

<details>
<summary><b> Arquivo CSV de histórico bloqueado</b></summary>
Se o arquivo CSV de disparo estiver aberto no Microsoft Excel durante a execução, o registrador redireciona o log para um arquivo alternativo para impedir o travamento da thread de envio.
</details>

---

## 📞 Suporte

Em caso de dúvidas técnicas ou reportes de erro, contate o setor de Tecnologia da Informação:

- 📧 **E-mail de Suporte:** `ti@didier.com.br`
- 🏷️ **Assunto:** `[CP Fani] Suporte Disparador de E-mails`

---

<p align="center">
  <sub>CP Fani © 2026 — Todos os direitos reservados. Uso estritamente interno.</sub>
</p>