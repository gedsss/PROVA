# Prova Técnica – Enriquecimento de Municípios (IBGE)

## Pré-requisitos

- Python 3.10+
- Biblioteca `requests`

## Instalação

```bash
pip install requests
```

## Como rodar

1. Edite o arquivo `main.py` e preencha suas credenciais:

```python
EMAIL = "seu_email@exemplo.com"
SENHA = "sua_senha_aqui"
```

2. Certifique-se de que o `input.csv` está na mesma pasta.

3. Execute:

```bash
python main.py
```

4. O programa irá:
   - Ler `input.csv`
   - Consultar a API do IBGE
   - Gerar `resultado.csv`
   - Exibir estatísticas no console
   - Fazer login no Supabase e enviar os resultados para correção

## Estrutura dos arquivos

| Arquivo         | Descrição                                      |
|-----------------|-------------------------------------------------|
| `main.py`       | Programa principal                              |
| `input.csv`     | Arquivo de entrada com municípios e populações  |
| `resultado.csv` | Arquivo gerado com dados enriquecidos do IBGE   |
| `README.md`     | Este arquivo                                    |

AVISO: Continuo recebendo erro 400 para as credenciais do SUPABASE mesmo estando corretas