from src.services.episode_context import EpisodeContextBuilder

builder = EpisodeContextBuilder()
ctx1 = builder.build_context(book_id=1, ep_num=1)
ctx2 = builder.build_context(book_id=1, ep_num=2)
ctx3 = builder.build_context(book_id=1, ep_num=3)
builder._episode_history = [
    {"ep_num": 1, "context": ctx1},
    {"ep_num": 2, "context": ctx2},
    {"ep_num": 3, "context": ctx3},
]
print("Before:")
for i, item in enumerate(builder._episode_history):
    print(f"  {i}: ep_num={item['ep_num']}, is_last={item['context'].get('is_last')}")

builder.set_final_episode(2)
print("\nAfter setting final episode to 2:")
for i, item in enumerate(builder._episode_history):
    print(f"  {i}: ep_num={item['ep_num']}, is_last={item['context'].get('is_last')}")