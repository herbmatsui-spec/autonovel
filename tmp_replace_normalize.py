import pathlib

path = pathlib.Path(r"I:\autonovel\autonovel\src\backend\sanitizer.py")
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

old_start = 338
old_end = 542

new_text = (
    "    _normalization_flow = NormalizationFlow()\n"
    "\n"
    "    @staticmethod\n"
    "    def normalize_metadata(data: Any, key_name: Optional[str] = None, is_root: bool = True) -> Any:\n"
    '        """AIが生成するメタデータ構造の揺れ（ネスト・キー名）を吸収して正規化する"""\n'
    "        return OutputSanitizer._normalization_flow.normalize_metadata(data, key_name, is_root)\n"
)

new_lines = lines[:old_start] + [new_text] + lines[old_end + 1 :]
path.write_text("".join(new_lines), encoding="utf-8")
print("Replaced lines", old_start, "-", old_end)
