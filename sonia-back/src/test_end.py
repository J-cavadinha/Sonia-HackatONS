import requests
import json


def test_analyze():
    try:
        print("🧪 Testando rota /analyze...")

        # Teste 1: Pergunta simples
        response = requests.post("http://localhost:8000/analyze", json={
            "question": "Para o último ano de dados disponível, qual foi o subsistema com a maior geração média total de energia? Adicionalmente, compare a geração mensal média entre os subsistemas Nordeste e Sul nesse período.",
            "chat_history": []
        })

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ JSON retornado:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Erro: {response.text}")

    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    test_analyze()