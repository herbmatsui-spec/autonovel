from src.services.exporters.ruby_parser import parse_ruby_to_xhtml, parse_bouten
from src.services.exporters.tcy_formatter import apply_tatechuyoko

t = "｜勇者《ゆうしゃ》は《《覚醒》》し第12章へ"
t = apply_tatechuyoko(parse_bouten(parse_ruby_to_xhtml(t)))
assert "<ruby>" in t
assert '<span class="bouten">' in t
assert '<span class="tcy">' in t
print("Part 4 Checkpoint PASS")
