import fakeredis
from src.stores.vector_store import RedisVectorStore
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.annotations.persistence import AnnotationPersistence

redis_client = fakeredis.FakeRedis(decode_responses=True)
vector_store = RedisVectorStore(skip_connection_check=True)
vector_store.client = redis_client

sample_beats = [
    {"source": "A", "target": "B", "emotion": "fear", "delta": 0.8, "cause": "test", "confidence": 0.9, "hidden": True},
    {"source": "B", "target": "A", "emotion": "sadness", "delta": 0.6, "cause": "test2", "confidence": 0.8, "hidden": False},
]

# Test persistence
persistence = AnnotationPersistence(vector_store)
# Convert to EmotionalBeat objects
from src.annotations.beat import EmotionalBeat
from src.pipeline.emotional_residue import EmotionType

beats = [
    EmotionalBeat(14, 3, "A", "B", EmotionType.FEAR, 0.8, "test", confidence=0.9, hidden=True),
    EmotionalBeat(14, 3, "B", "A", EmotionType.SADNESS, 0.6, "test2", confidence=0.8, hidden=False),
]

persistence.persist_beats(beats, 14)

# Check what keys were stored
keys = vector_store.get_namespace_keys("annotation")
print("Keys:", keys)

# Try to get
stored = vector_store.get_latest("annotation", ("A", "B"))
print("Stored:", stored)

if stored:
    print("Value:", stored.get_value("A", "B", "fear"))