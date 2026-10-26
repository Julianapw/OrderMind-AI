
import json
from pathlib import Path

from app.evaluation.evaluate_agent import (
    analysis_to_text,
    evaluate_response,
)

RESULTS_DIR = Path("evaluation_results")

QUOTA_ERROR_TERMS = (
    "429",
    "resource_exhausted",
    "quota exceeded",
    "rate limit",
    "too many requests",
)


def get_status(result: dict) -> str:
    """Identify the result status, including older JSON files."""
    status = result.get("status")

    if status:
        return status

    error = result.get("error")

    if error:
        error_lower = error.lower()

        if any(term in error_lower for term in QUOTA_ERROR_TERMS):
            return "api_quota_error"

        return "execution_error"

    if result.get("analysis") is not None or result.get("response"):
        return "completed"

    return "unknown"


def main() -> None:
    if not RESULTS_DIR.exists():
        print("A pasta de resultados ainda não existe.")
        return

    files = sorted(RESULTS_DIR.glob("evaluation_*.json"))

    if not files:
        print("Nenhum arquivo de avaliação encontrado.")
        return

    latest_file = files[-1]
    print(f"Arquivo analisado: {latest_file}")

    try:
        with latest_file.open("r", encoding="utf-8") as file:
            results = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Não foi possível ler o arquivo: {exc}")
        return

    if not isinstance(results, list):
        print("Formato de arquivo inválido: esperava uma lista.")
        return

    for result in results:
        if not isinstance(result, dict):
            print("\nRegistro inválido: esperado um objeto JSON.")
            continue

        print(f"\nCaso: {result.get('case', 'não identificado')}")

        status = get_status(result)
        print(f"Status: {status}")

        if status == "not_executed":
            print(
                result.get(
                    "reason",
                    "Caso não executado.",
                )
            )
            continue

        if result.get("error"):
            print(f"Motivo: {result['error'][:300]}")
            continue

        analysis = result.get("analysis")

        # Compatibilidade com resultados estruturados e arquivos antigos.
        if analysis is not None:
            response_text = analysis_to_text(analysis)
        else:
            response = result.get("response")
            response_text = (
                response
                if isinstance(response, str)
                else ""
            )

        if not response_text.strip():
            print("Nenhuma análise ou resposta encontrada.")
            continue

        # Recalcula as verificações gerais usando o texto salvo.
        checks = evaluate_response(response_text)

        print("Verificações automáticas:")
        print(
            json.dumps(
                checks,
                ensure_ascii=False,
                indent=2,
            )
        )

        # Mostra as verificações específicas já registradas.
        scenario_checks = result.get("scenario_checks")

        if scenario_checks is not None:
            print("Verificações específicas do cenário:")
            print(
                json.dumps(
                    scenario_checks,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        if "requires_human_review" in result:
            print(
                "Revisão humana necessária:",
                result["requires_human_review"],
            )


if __name__ == "__main__":
    main()
