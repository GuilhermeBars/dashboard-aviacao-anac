# Publicar o dashboard no Hugging Face Spaces

Objetivo: deixar o dashboard numa **URL pública** que os colegas abrem em qualquer
computador com navegador e internet — sem instalar nada.

O que já está pronto (eu fiz): o app aceita a base enxuta de 5 MB, lê os rótulos
de um JSON e usa porta por variável de ambiente. O script `build_deploy.py` gera a
pasta **`deploy_hf/`** autocontida (código + dados de 5 MB + Dockerfile). É essa
pasta que sobe pro Hugging Face.

---

## Passo 1 — Criar a conta e o token

1. Acesse <https://huggingface.co/join> e crie a conta (pode logar com Google/GitHub).
2. Crie um **token de escrita**: <https://huggingface.co/settings/tokens> →
   *New token* → tipo **Write** → copie o token (algo como `hf_xxx...`).
   Esse token é a "senha" que o `git push` vai pedir.

## Passo 2 — Criar o Space

1. Acesse <https://huggingface.co/new-space>.
2. Preencha:
   - **Owner**: seu usuário.
   - **Space name**: por exemplo `dashboard-aviacao-anac`.
   - **License**: pode deixar em branco ou `mit`.
   - **Space SDK**: escolha **Docker** → *Blank / Dockerfile*.
   - **Visibility**: **Public** (importante: assim os colegas não precisam logar).
3. Clique em **Create Space**. Anote a URL do repositório, no formato:
   `https://huggingface.co/spaces/SEU-USUARIO/dashboard-aviacao-anac`

## Passo 3 — Gerar a pasta de deploy (se ainda não gerou)

No terminal, na raiz do projeto:

```bash
source .venv/bin/activate
python build_deploy.py
```

Isso (re)cria a pasta `deploy_hf/` com a base de 5 MB e tudo que o Space precisa.

## Passo 4 — Enviar a pasta para o Space

```bash
cd deploy_hf

git init
git add .
git commit -m "Dashboard aviacao ANAC 2024"
git branch -M main
git remote add origin https://huggingface.co/spaces/SEU-USUARIO/dashboard-aviacao-anac
git push -u origin main
```

Quando o `git push` pedir:
- **Username**: seu usuário do Hugging Face.
- **Password**: cole o **token de escrita** (`hf_...`) do Passo 1 (não é a senha do site).

## Passo 5 — Esperar o build e abrir

1. Volte à página do Space no navegador. Ele vai mostrar **"Building"** (o Hugging
   Face monta o Docker — leva ~2 a 4 minutos na primeira vez).
2. Quando virar **"Running"**, o dashboard está no ar. A URL pública para mandar
   pros colegas é:

   **`https://SEU-USUARIO-dashboard-aviacao-anac.hf.space`**

   (também dá pra abrir clicando no Space e usando o botão de tela cheia.)

Pronto. Qualquer pessoa com esse link abre o dashboard interativo, de qualquer
máquina.

---

## Atualizar depois (se mudar o dashboard)

```bash
python build_deploy.py          # regenera a pasta deploy_hf (mantém o .git)
cd deploy_hf
git add -A
git commit -m "Atualiza dashboard"
git push                        # o Space rebuilda sozinho
```

## Dúvidas comuns

- **"O Space dormiu / demora a abrir"**: depois de dias sem acesso ele hiberna; o
  primeiro acesso leva ~30s pra acordar. Para a apresentação, abra o link 1 min antes.
- **"Authentication failed" no push**: você usou a senha do site em vez do **token**.
  Refaça com o token `hf_...` no lugar da senha.
- **Arquivo grande**: não há. O maior arquivo é a base de 5,2 MB, abaixo do limite
  de 10 MB do Hugging Face, então não precisa de Git LFS.
- **Quero deixar privado**: pode, mas aí cada colega precisaria logar no HF. Para o
  trabalho, deixe **Public**.
```
