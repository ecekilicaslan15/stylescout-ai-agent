from pathlib import Path

from services.rag_service import RagService

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"


def _headings(results) -> list[str]:
    return [result.heading for result in results]


def _print_results(query: str, results) -> None:
    print(f"\nQuery: {query}")
    if not results:
        print("No relevant chunks retrieved.")
        return

    for result in results:
        print(f"- Heading: {result.heading}")
        print(f"  Source: {result.source}")
        print(f"  Score: {result.score}")
        print(f"  Content: {result.content[:180]}{'...' if len(result.content) > 180 else ''}")


def run_tests() -> None:
    rag = RagService(KNOWLEDGE_DIR)

    hot_weather_query = "What fabric is suitable for hot weather?"
    hot_results = rag.retrieve(hot_weather_query, top_k=3)
    _print_results(hot_weather_query, hot_results)
    hot_headings = _headings(hot_results)
    assert any(heading in {"Linen", "Cotton"} for heading in hot_headings), hot_headings

    winter_query = "What should I use for a cold winter coat?"
    winter_results = rag.retrieve(winter_query, top_k=3)
    _print_results(winter_query, winter_results)
    assert "Wool" in _headings(winter_results), _headings(winter_results)

    delicate_query = "Which material needs delicate care?"
    delicate_results = rag.retrieve(delicate_query, top_k=3)
    _print_results(delicate_query, delicate_results)
    assert "Silk" in _headings(delicate_results), _headings(delicate_results)

    unrelated_query = "How do I configure a PostgreSQL database cluster?"
    unrelated_results = rag.retrieve(unrelated_query, top_k=3)
    _print_results(unrelated_query, unrelated_results)
    assert unrelated_results == [], unrelated_results

    print("\nAll RAG v1 tests passed.")


if __name__ == "__main__":
    run_tests()
