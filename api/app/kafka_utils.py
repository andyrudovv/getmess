import os
import json
from typing import Awaitable, Callable, Optional, List
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

_producer: AIOKafkaProducer | None = None
_broadcast_cb: Optional[Callable[[List[int], dict], Awaitable[None]]] = None

async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKER)
        await _producer.start()
    return _producer

def set_broadcast_callback(cb: Callable[[List[int], dict], Awaitable[None]]):
    global _broadcast_cb
    _broadcast_cb = cb

async def ensure_topic(topic: str):
    admin = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BROKER)
    try:
        topics = await admin.list_topics()
        if topic not in topics:
            await admin.create_topics([NewTopic(name=topic, num_partitions=1, replication_factor=1)])
    finally:
        await admin.close()

async def start_consumer_loop(topic: str, recipients_resolver):
    """Start consumer; on message resolve recipients and broadcast."""
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BROKER,
        group_id="chat-consumer",
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                user_ids = await recipients_resolver(payload)
                if _broadcast_cb and user_ids:
                    await _broadcast_cb(user_ids, {"type": "message.new", "data": payload})
            except Exception as e:
                print(f"[Kafka] error processing message: {e!r}")
    finally:
        await consumer.stop()
