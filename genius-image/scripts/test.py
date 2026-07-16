import importlib.util
import os
import atexit
import shutil
import tempfile
from pathlib import Path
HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('genius', HERE / 'genius.py')
genius = importlib.util.module_from_spec(spec)
spec.loader.exec_module(genius)

TMP_ROOT = Path(tempfile.mkdtemp(prefix='genius_image_test_'))
atexit.register(lambda: shutil.rmtree(TMP_ROOT, ignore_errors=True))
OUT_DIR = TMP_ROOT / 'genius_output'
LOG_DIR = OUT_DIR / 'Logs'
genius.OUT_DIR = OUT_DIR
genius.LOG_DIR = LOG_DIR
genius.LOG_FILE = LOG_DIR / 'genius_log.jsonl'
OUT_DIR.mkdir(exist_ok=True)

print('=== Skill 加载健康检查 ===')
required = ['build_payload', 'submit', 'get_balance', 'find_next_filename', 'write_log',
            'clean_old_logs', 'load_batch', 'validate_task', 'extract_media_urls',
            'resolve_refs', 'run_preflight', 'run_single', 'run_batch', 'run_fetch_task',
            'wait_for_completion', 'log_print', 'safe_filename_stem', 'make_output_basename',
            'emit_result', 'setup_delivery', 'pick_webhook_port', 'main']
missing = [f for f in required if not hasattr(genius, f)]
if missing:
    print(f'  FAIL: missing {missing}')
else:
    print(f'  PASS: all {len(required)} functions present')
print(f'  MODELS: {list(genius.MODELS.keys())}')
print(f'  WEBHOOK_PORT: {genius.WEBHOOK_PORT}')

print('=== build_payload 测试 ===')
ok = 0
for model in ['gpt-image-2', 'gpt-image-2-premium', 'nano-banana-2', 'nano-banana-2-lite']:
    task = {'prompt': 'test', 'model': model, 'aspect': '16:9'}
    if model in ('gpt-image-2', 'gpt-image-2-premium', 'nano-banana-2'):
        task['resolution'] = '1K'
    if model == 'gpt-image-2-premium': task['quality'] = 'low'
    if model == 'nano-banana-2': task['google_search'] = True
    p = genius.build_payload(task, 'https://test.com/webhook')
    keys = list(p['input'].keys())
    print(f'  {model:25} -> {p["model"]}  input keys: {keys}')
    ok += 1
print(f'  PASS ({ok}/4 models)')

print()
print('=== find_next_filename 测试 ===')
for f in OUT_DIR.glob('test_find_*'):
    f.unlink()
results = []
for i in range(1, 4):
    f = genius.find_next_filename('test_find', 'png', OUT_DIR)
    f.write_text(f'test{i}')
    results.append(f.name)
expected = ['test_find_1.png', 'test_find_2.png', 'test_find_3.png']
if results == expected:
    print(f'  PASS: {results}')
else:
    print(f'  FAIL: got {results}, expected {expected}')
for f in OUT_DIR.glob('test_find_*'):
    f.unlink()

print()
print('=== load_batch 测试 ===')
import json
batch_data = [
    {'prompt': 'test1', 'model': 'gpt-image-2'},
    {'prompt': 'test2', 'model': 'nano-banana-2', 'resolution': '4K'},
]
batch_file = TMP_ROOT / 'test_batch.json'
with open(batch_file, 'w', encoding='utf-8') as f:
    json.dump(batch_data, f, ensure_ascii=False)
tasks = genius.load_batch(str(batch_file))
batch_file.unlink()
if len(tasks) == 2 and tasks[0]['model'] == 'gpt-image-2' and tasks[1]['resolution'] == '4K':
    print(f'  PASS: loaded {len(tasks)} tasks')
else:
    print(f'  FAIL: {tasks}')

print()
print('=== 参考图数量校验测试 ===')
ok = 0
for model, limit in [('gpt-image-2', 16), ('gpt-image-2-premium', 14), ('nano-banana-2', 14), ('nano-banana-2-lite', 10)]:
    task = {'prompt': 'test', 'model': model, 'ref': ['url'] * (limit + 1)}
    try:
        genius.build_payload(task, 'https://test.com/webhook')
        print(f'  {model}: FAIL (should have raised)')
    except RuntimeError:
        print(f'  {model}: PASS (上限 {limit})')
        ok += 1
print(f'  Summary: {ok}/4 models enforce limits')

print()
print('=== 本地参考图转 base64 测试 ===')
ref_file = TMP_ROOT / 'ref.png'
ref_file.write_bytes(b'\x89PNG\r\n\x1a\n')
resolved = genius.resolve_refs([str(ref_file), 'https://example.com/ref.png'])
if resolved[0].startswith('data:image/png;base64,') and resolved[1] == 'https://example.com/ref.png':
    print('  PASS: local path converted and URL preserved')
else:
    print(f'  FAIL: {resolved}')

print()
print('=== 模型参数约束测试 ===')
# should_raise: True = expect RuntimeError
checks = [
    ({'prompt': 'test', 'model': 'gpt-image-2', 'aspect': '1:1', 'resolution': '4K'}, True, 'gpt-image-2 rejects 4K 1:1'),
    ({'prompt': 'test', 'model': 'gpt-image-2', 'aspect': 'auto', 'resolution': '2K'}, True, 'gpt-image-2 rejects auto non-1K'),
    # premium currently allows 21:9 and 4K per MODELS config
    ({'prompt': 'test', 'model': 'gpt-image-2-premium', 'aspect': '21:9', 'resolution': '1K'}, False, 'premium allows 21:9'),
    ({'prompt': 'test', 'model': 'gpt-image-2-premium', 'aspect': '1:1', 'resolution': '4K'}, False, 'premium allows 4K'),
]
ok = 0
for task, should_raise, label in checks:
    try:
        genius.validate_task(task)
        if should_raise:
            print(f'  {label}: FAIL (should have raised)')
        else:
            print(f'  {label}: PASS')
            ok += 1
    except RuntimeError:
        if should_raise:
            print(f'  {label}: PASS')
            ok += 1
        else:
            print(f'  {label}: FAIL (should have accepted)')
print(f'  Summary: {ok}/{len(checks)} constraints enforced')

print()
print('=== 文件名 / poll-only payload 测试 ===')
stem = genius.safe_filename_stem('Genius Design 技能说明书!')
base = genius.make_output_basename('gpt-image-2', '一只猫', name='cute-cat')
payload_poll = genius.build_payload({'prompt': 'x', 'model': 'gpt-image-2'}, None)
payload_hook = genius.build_payload({'prompt': 'x', 'model': 'gpt-image-2'}, 'https://cb.example/webhook')
fn_ok = ('技能' in stem) and base == 'cute-cat'
pl_ok = ('callback_url' not in payload_poll) and payload_hook.get('callback_url') == 'https://cb.example/webhook'
if fn_ok and pl_ok:
    print(f'  PASS: stem={stem!r} base={base!r} poll_only_omits_callback=True')
else:
    print(f'  FAIL: stem={stem!r} base={base!r} poll_keys={list(payload_poll.keys())}')

print()
print('=== media_urls 提取测试 ===')
media_case = {'result': {'media_urls': ['https://example.com/a.png', 'https://example.com/b.png']}}
media_urls = genius.extract_media_urls(media_case)
if media_urls == ['https://example.com/a.png', 'https://example.com/b.png']:
    print('  PASS: media_urls preserved')
else:
    print(f'  FAIL: {media_urls}')

print()
print('=== preflight 安全闸测试 ===')
try:
    genius.run_preflight(False)
    print('  FAIL: preflight without --no-gen should fail')
except RuntimeError:
    print('  PASS: --preflight requires --no-gen')

print()
print('=== 日志轮转测试 ===')
log = LOG_DIR / 'genius_log.jsonl'
LOG_DIR.mkdir(exist_ok=True)
for f in LOG_DIR.glob('genius_log_*.jsonl'):
    f.unlink()
old_max_size = genius.LOG_MAX_SIZE
try:
    genius.LOG_MAX_SIZE = 128
    log.write_text('x' * 256)
    genius.write_log({'test': True})
    archives = list(LOG_DIR.glob('genius_log_*.jsonl'))
    if archives and log.stat().st_size < 100:
        print(f'  PASS: rotated to {archives[0].name}')
        archives[0].unlink()
        log.unlink()
    else:
        print(f'  FAIL: archives={archives}, current size={log.stat().st_size if log.exists() else 0}')
finally:
    genius.LOG_MAX_SIZE = old_max_size

print()
print('=== 自检完成 ===')
