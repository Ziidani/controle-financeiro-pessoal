# Aplicativo de Controle Financeiro Pessoal

Um aplicativo desktop completo para gerenciamento financeiro pessoal desenvolvido em Python com PyQt5.

## Funcionalidades

- ✅ **Sistema de autenticação de usuários**
- ✅ **Gestão de transações (receitas e despesas)**
- ✅ **Sistema de orçamentos por categoria**
- ✅ **Metas financeiras com acompanhamento de progresso**
- ✅ **Dashboard com gráficos e resumo financeiro**
- ✅ **Exportação de relatórios em PDF e Excel**
- ✅ **Sincronização com nuvem (Cloudinary)**
- ✅ **Interface gráfica intuitiva e responsiva**

## Tecnologias Utilizadas

- Python 3.8+
- PyQt5 para interface gráfica
- SQLite para persistência de dados
- Matplotlib para visualização de gráficos
- Pandas para manipulação de dados
- ReportLab para geração de PDF
- Cloudinary para sincronização na nuvem

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/controle-financeiro-pessoal.git
cd controle-financeiro-pessoal
```

2. Crie um ambiente virtual (recomendado):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
Crie uma conta no Cloudinary

Crie um arquivo .env na pasta do projeto com:

```text
CLOUDINARY_CLOUD_NAME=seu_cloud_name
CLOUDINARY_API_KEY=sua_api_key
CLOUDINARY_API_SECRET=sua_api_secret
```

## Uso
Execute o aplicativo:
```bash
python finance_app.py
```

## Estrutura do Projeto
```text

controle-financeiro-pessoal/
├── finance_app.py          # Código principal da aplicação
├── requirements.txt        # Dependências do projeto
├── .env                   # Variáveis de ambiente (não versionado)
├── .gitignore            # Arquivos a serem ignorados pelo Git
├── README.md             # Este arquivo
└── finance_manager.db    # Banco de dados (gerado automaticamente)
```

## Contribuição

1. Faça um fork do projeto

2. Crie uma branch para sua feature (git checkout -b feature/AmazingFeature)

3. Commit suas mudanças (git commit -m 'Add some AmazingFeature')

4. Push para a branch (git push origin feature/AmazingFeature)

5. Abra um Pull Request

# Licença
Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

# Contato

Daniel Nunes Novaes - @ziidani - danieln1703@gmail.com

Link do projeto: https://github.com/ziidani/controle-financeiro-pessoal
