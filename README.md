# ✉️ Disparador de E-mails CP Fani

> Aplicação desktop robusta desenvolvida em Python para disparo personalizado e automatizado de e-mails corporativos em massa para revendedores.

---

## 📌 Índice

- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-funcionalidades)
- [Requisitos do Sistema](#-requisitos-do-sistema)
- [Instalação e Configuração](#-instalação-e-configuração)
- [Guia de Configuração SMTP](#-guia-de-configuração-smtp)
- [Como Utilizar](#-como-utilizar)
- [Boas Práticas Anti-Spam](#-boas-práticas-anti-spam)
- [Conformidade com a LGPD](#-conformidade-com-a-lgpd)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Solução de Problemas](#-solução-de-problemas)
- [Build e Empacotamento](#-build-e-empacotamento)
- [Suporte](#-suporte)

---

## 🚀 Visão Geral

O **Disparador de E-mails CP Fani** foi criado para simplificar o envio de comunicados corporativos, promoções e avisos para bases de revendedores. Ele alia a facilidade de uma interface gráfica nativa à segurança do armazenamento de credenciais no SO e boas práticas de entrega para evitar que suas mensagens caiam no spam.

---

## ✨ Funcionalidades

- 📬 **Suporte Multi-Provedor:** Suporte nativo para Gmail e GoDaddy.
- 🎨 **Editor de HTML com Pré-visualização:** Interface visual com suporte a formatação, imagens e anexos.
- 🏷️ **Personalização Dinâmica:** Substituição automática de variáveis como `{{primeiro_nome}}`, `{{codigo}}`, etc.
- 📊 **Importação Inteligente:** Leitura de planilhas Excel (`.xlsx`) e arquivos `.csv` com detecção de colunas e tratamento de duplicados.
- 🔒 **Segurança Nativa:** Salvamento de senhas via Cofre do Sistema Operacional (`keyring`).
- ⏱️ **Controle de Vazão:** Ajuste fino de intervalo entre envios e limite diário pré-definido.
- 📝 **Auditoria e Logs:** Geração automática de relatórios de disparo em CSV.

---

## 📋 Requisitos do Sistema

| Requisito | Especificação Mínima | Recomendado |
|---|---|---|
| **Linguagem** | Python 3.10+ | Python 3.12 |
| **Sistema Operacional** | Windows 10, Linux, macOS | Windows 11 |
| **Memória RAM** | 4 GB | 8 GB+ |
| **Espaço em Disco** | 500 MB libre | 1 GB livre |

---

## 💻 Instalação e Configuração

### 1. Clonar o Repositório

```bash
git clone https://github.com/sunstrix/Disparador-de-emails-CP-FANI.git
cd Disparador-de-emails-CP-FANI
```

### 2. Configurar o Ambiente Virtual

- **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```

- **Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 4. Executar a Aplicação

```bash
python main.py
```

---

## ⚙️ Guia de Configuração SMTP

### 🔴 Gmail (Google Workspace ou Pessoal)

> ⚠️ **Atenção:** O Gmail não aceita mais a sua senha padrão em conexões externas. É **obrigatório** utilizar uma **Senha de App**.

1. Acesse as [Configurações de Segurança do Google](https://myaccount.google.com/security).
2. Certifique-se de que a **Verificação em duas etapas** está **ativada**.
3. Navegue até a seção de [Senhas de App](https://myaccount.google.com/apppasswords).
4. Crie um app chamado `Disparador CP Fani` e copie a chave de 16 caracteres gerada.
5. No aplicativo, selecione `Gmail`, a porta `STARTTLS (587)` ou `SSL (465)`, e insira essa senha de 16 caracteres.

---

### 🔵 GoDaddy

1. Verifique os limites do seu plano na [Central GoDaddy](https://dcc.godaddy.com/manage/email) (geralmente entre 250 a 500 mensagens/dia).
2. No aplicativo, selecione `GoDaddy`, a porta `SSL (465)` e insira sua senha normal de e-mail.

---

## 🕹️ Como Utilizar

```
+-----------------------------------------------------------------------+
|  [1] SMTP  -->  [2] Destinatários  -->  [3] Mensagem  -->  [4] Envio  |
+-----------------------------------------------------------------------+
```

1. **Aba "Configuração SMTP":** Preencha os dados do servidor, teste a conexão e salve as credenciais com segurança no cofre do sistema.
2. **Aba "Destinatários":** Selecione o arquivo `.xlsx` ou `.csv`. O sistema mapeia os campos automaticamente e indica e-mails inválidos ou duplicados.
3. **Aba "Mensagem":** Insira o assunto e crie seu corpo de mensagem usando tag de personalização (ex: `Olá {{primeiro_nome}}`).
4. **Aba "Envio":** Defina o limite diário, ajuste o atraso entre mensagens (recomendado: 10 a 30 segundos) e acompanhe o progresso.
5. **Aba "Log":** Acompanhe o status em tempo real e consulte o relatório exportado na pasta `logs/`.

---

## 🛡️ Boas Práticas Anti-Spam

Para garantir a máxima entregabilidade na caixa de entrada dos revendedores, certifique-se de configurar a autenticação do seu domínio no painel DNS:

### Registros DNS Essenciais

- **SPF (Sender Policy Framework):**
  - *Gmail:* `v=spf1 include:_spf.google.com ~all`
  - *GoDaddy:* `v=spf1 include:spf.godaddy.com ~all`
- **DMARC:**
  - `v=DMARC1; p=none; rua=mailto:ti@didier.com.br`

### Aquecimento de Contas Novas (*Warm-up*)

```
Semana 1  -->  50  e-mails/dia
Semana 2  -->  100 e-mails/dia
Semana 3  -->  150 e-mails/dia
Semana 4+ -->  200 e-mails/dia (Máximo recomendado)
```

---

## 🔒 Conformidade com a LGPD

- **Privacidade Local:** Os dados dos destinatários e relatórios residem unicamente em sua máquina local e não são submetidos a serviços externos.
- **Armazenamento Seguro:** As senhas SMTP são gerenciadas de forma criptografada pelo cofre nativo do SO (`keyring`).
- **Descadastro:** Recomenda-se incluir ao final do modelo HTML o link de opt-out:

```html
<p style="font-size: 11px; color: #777777;">
  Caso não deseje mais receber nossos comunicados, 
  <a href="mailto:descadastro@seudominio.com?subject=Cancelar%20Inscricao">clique aqui para se descadastrar</a>.
</p>
```

---

## 📂 Estrutura do Projeto

```
Disparador-de-emails-CP-FANI/
├── main.py                   # Ponto de entrada da aplicação
├── requirements.txt          # Lista de dependências Python
├── README.md                 # Documentação do projeto
├── .gitignore                # Exclusão de arquivos sensíveis/temporários
├── app/
│   ├── config.py             # Configurações globais e diretórios
│   ├── ui/
│   │   ├── main_window.py    # Interface gráfica principal e navegação
│   │   └── components.py     # Componentes visuais e edições de tabela
│   └── core/
│       ├── importer.py       # Leitura e validação de planilhas
│       ├── template_engine.py# Processamento de tags dinâmicas
│       ├── smtp_client.py    # Conectividade SMTP e envio MIME
│       ├── sender_worker.py  # Gerenciamento de thread paralela
│       └── logger.py         # Gravação de histórico e exportação CSV
├── assets/                   # Imagens e recursos de marca
├── logs/                     # Relatórios de envio gerados em runtime
└── templates/                # Modelos de mensagens armazenados
```

---

## 🛠️ Solução de Problemas

<details>
<summary><b> Erro de Autenticação (Gmail)</b></summary>
Certifique-se de estar utilizando a <b>Senha de App</b> de 16 dígitos e não a sua senha comum do e-mail.
</details>

<details>
<summary><b> Limite diário atingido</b></summary>
Aguarde o reset de 24 horas do seu provedor ou altere a conta remetente.
</details>

<details>
<summary><b> Imagens corrompidas ou quebradas no e-mail</b></summary>
Verifique se a imagem local está em formato `.png` ou `.jpg` e não ultrapassa 2MB de tamanho.
</details>

---

## 📦 Build e Empacotamento

Para compilar e gerar o executável standalone para **Windows (`.exe`)**:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/logo.ico main.py
```

O arquivo final será armazenado na pasta `/dist`.

---

## 📞 Suporte

Em caso de dúvidas, divergências ou sugestões, entre em contato com a equipe interna de tecnologia:

- 📧 **E-mail:** `ti@didier.com.br`
- 🏷️ **Assunto:** `[CP Fani] Suporte Disparador de E-mails`

---

<p align="center">
  <sub>CP Fani © 2026 — Todos os direitos reservados. Uso estritamente interno.</sub>
</p>