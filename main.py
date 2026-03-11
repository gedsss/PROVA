import csv
import json
import sys
import unicodedata
from difflib import SequenceMatcher
from collections import defaultdict
try:
    import requests
except ImportError:
    print("ERRO: O módulo 'requests' não está instalado.")
    print("Instale com:  pip install requests")
    sys.exit(1)
from dotenv import load_dotenv
import os

load_dotenv()  # carrega as variáveis do .env

supabase_url = os.getenv("SUPABASE_URL")
supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
ibge_municipios_url = os.getenv("IBGE_MUNICIPIOS_URL")
submit_url = os.getenv("SUBMIT_URL")
input_file = os.getenv("INPUT_FILE")
output_file = os.getenv("OUTPUT_FILE")
similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "70"))


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    texto = texto.strip().lower()
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(sem_acento.split())


def similaridade(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def buscar_municipios_ibge() -> list[dict]:
    print("Buscando lista de municípios na API do IBGE...")
    try:
        resp = requests.get(ibge_municipios_url, timeout=30)
        resp.raise_for_status()
        dados = resp.json()
        print(f"{len(dados)} municípios carregados do IBGE.")
        return dados
    except requests.RequestException as e:
        print(f"Falha ao acessar API do IBGE: {e}")
        return []


def construir_indice(municipios_ibge: list[dict]) -> dict:
    indice = {}
    for m in municipios_ibge:
        nome_norm = normalizar(m["nome"])
        indice[nome_norm] = m
    return indice


def extrair_info(municipio_ibge: dict) -> dict:
    uf = municipio_ibge["microrregiao"]["mesorregiao"]["UF"]
    return {
        "municipio_ibge": municipio_ibge["nome"],
        "uf": uf["sigla"],
        "regiao": uf["regiao"]["nome"],
        "id_ibge": municipio_ibge["id"],
    }


def encontrar_municipio(nome_input: str, indice: dict, lista_ibge: list[dict]) -> tuple[dict | None, str]:
    nome_norm = normalizar(nome_input)

    if nome_norm in indice:
        info = extrair_info(indice[nome_norm])
        return info, "OK"
    melhor_score = 0.0
    melhor_municipio = None
    segundo_score = 0.0

    for m in lista_ibge:
        score = similaridade(nome_norm, normalizar(m["nome"]))
        if score > melhor_score:
            segundo_score = melhor_score
            melhor_score = score
            melhor_municipio = m
        elif score > segundo_score:
            segundo_score = score
    if melhor_score >= similarity_threshold:
        if (melhor_score - segundo_score) < 0.03 and segundo_score >= similarity_threshold:
            info = extrair_info(melhor_municipio)
            return info, "AMBIGUO"

        info = extrair_info(melhor_municipio)
        return info, "OK"

    return None, "NAO_ENCONTRADO"


def fazer_login(email: str, senha: str) -> str | None:
    print("Fazendo login no Supabase...")
    url = f"{supabase_url}/auth/v1/token?grant_type=password"
    headers = {
        "Content-Type": "application/json",
        "apikey": supabase_anon_key,
    }
    payload = {"email": email, "password": senha}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        dados = resp.json()
        token = dados.get("access_token")
        if token:
            print("Login realizado com sucesso!")
            return token
        else:
            print("Resposta do login não contém access_token.")
            return None
    except requests.RequestException as e:
        print(f"Falha no login: {e}")
        return None


def enviar_resultados(stats: dict, access_token: str) -> None:
    print("Enviando estatísticas para a API de correção...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"stats": stats}

    try:
        resp = requests.post(submit_url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        resultado = resp.json()
        print("\n" + "=" * 60)
        print("RESULTADO DA CORREÇÃO")
        print("=" * 60)
        print(f"  Score : {resultado.get('score', 'N/A')}")
        print(f"  Feedback: {resultado.get('feedback', 'N/A')}")
        componentes = resultado.get("components", {})
        if componentes:
            print("  Componentes:")
            for chave, valor in componentes.items():
                print(f"    - {chave}: {valor}")
        print("=" * 60)
    except requests.RequestException as e:
        print(f"Falha ao enviar resultados: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"  Resposta: {e.response.text}")

def main():
    EMAIL = "gabriel.developer1988@gmail.com"    
    SENHA = "22Ed22ed22ed@"      

   
    print(f"Lendo {input_file}")
    try:
        with open(input_file, encoding="utf-8") as f:
            leitor = csv.DictReader(f)
            entradas = list(leitor)
        print(f"{len(entradas)} linhas lidas.")
    except FileNotFoundError:
        print(f"Arquivo {input_file} não encontrado.")
        sys.exit(1)

    lista_ibge = buscar_municipios_ibge()
    if not lista_ibge:
        print("API do IBGE indisponível.")

    indice = construir_indice(lista_ibge) if lista_ibge else {}
    resultados = []
    for entrada in entradas:
        municipio_input = entrada["municipio"]
        populacao_input = entrada["populacao"]

        if not lista_ibge:
            resultados.append({
                "municipio_input": municipio_input,
                "populacao_input": populacao_input,
                "municipio_ibge": "",
                "uf": "",
                "regiao": "",
                "id_ibge": "",
                "status": "ERRO_API",
            })
            continue

        info, status = encontrar_municipio(municipio_input, indice, lista_ibge)

        if info:
            resultados.append({
                "municipio_input": municipio_input,
                "populacao_input": populacao_input,
                "municipio_ibge": info["municipio_ibge"],
                "uf": info["uf"],
                "regiao": info["regiao"],
                "id_ibge": info["id_ibge"],
                "status": status,
            })
        else:
            resultados.append({
                "municipio_input": municipio_input,
                "populacao_input": populacao_input,
                "municipio_ibge": "",
                "uf": "",
                "regiao": "",
                "id_ibge": "",
                "status": status,
            })

    campos = [
        "municipio_input", "populacao_input", "municipio_ibge",
        "uf", "regiao", "id_ibge", "status",
    ]
    print(f" Gravando {output_file}...")
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(resultados)
    print(f"{output_file} gerado com {len(resultados)} linhas.")
    total_municipios = len(resultados)
    total_ok = sum(1 for r in resultados if r["status"] == "OK")
    total_nao_encontrado = sum(1 for r in resultados if r["status"] == "NAO_ENCONTRADO")
    total_erro_api = sum(1 for r in resultados if r["status"] == "ERRO_API")
    pop_total_ok = sum(
        int(r["populacao_input"])
        for r in resultados
        if r["status"] == "OK"
    )
    pop_por_regiao = defaultdict(list)
    for r in resultados:
        if r["status"] == "OK" and r["regiao"]:
            pop_por_regiao[r["regiao"]].append(int(r["populacao_input"]))

    medias_por_regiao = {}
    for regiao, pops in sorted(pop_por_regiao.items()):
        media = round(sum(pops) / len(pops), 2)
        medias_por_regiao[regiao] = media

    stats = {
        "total_municipios": total_municipios,
        "total_ok": total_ok,
        "total_nao_encontrado": total_nao_encontrado,
        "total_erro_api": total_erro_api,
        "pop_total_ok": pop_total_ok,
        "medias_por_regiao": medias_por_regiao,
    }

    print("\nRESULTADO POR MUNICÍPIO:")
    print(f"{'Input':<20} {'IBGE':<25} {'UF':<5} {'Região':<15} {'Status'}")
    print("-" * 85)
    for r in resultados:
        print(
            f"{r['municipio_input']:<20} "
            f"{r['municipio_ibge']:<25} "
            f"{r['uf']:<5} "
            f"{r['regiao']:<15} "
            f"{r['status']}"
        )

    if EMAIL and SENHA:
        token = fazer_login(EMAIL, SENHA)
        if token:
            enviar_resultados(stats, token)
        else:
            print("Não foi possível obter o token. Resultados não enviados.")
    else:
        print("\nEMAIL/SENHA não preenchidos. Pulando envio.")
        print("  Para enviar, edite as variáveis EMAIL e SENHA em main.py")

    print("\nFinalizando....")


if __name__ == "__main__":
    main()