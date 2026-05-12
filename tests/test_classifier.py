from server.services.classifier import classify_topic


def test_classify_coding():
    topic, slugs = classify_topic("how do I write a FastAPI endpoint?")
    assert topic == "coding"
    assert isinstance(slugs, list)
    assert len(slugs) > 0


def test_classify_design():
    topic, slugs = classify_topic("what's the system architecture for microservices?")
    assert topic == "design"
    assert len(slugs) > 0


def test_classify_ml():
    topic, slugs = classify_topic("how does RAG work with embeddings?")
    assert topic == "ml"
    assert len(slugs) > 0


def test_classify_general_fallback():
    topic, slugs = classify_topic("hello, how are you?")
    assert topic == "general"
    assert len(slugs) > 0


def test_classify_empty_question():
    topic, slugs = classify_topic("")
    assert topic == "general"
