#!/usr/bin/env python3
"""Compare actual old/new compiled helpers under explicit, stable native models.

Does not replace production functions, execute main, or model Warcraft's engine.
"""
from pathlib import Path
import ctypes
import gzip
import hashlib
import importlib.util
import json
import os
import random
import re
import time

BASE = Path('/workspace/scratch/243ebc79fa0a')
OUT = Path(__file__).resolve().parent / 'parity'
NEW = OUT.parent / 'war3map.lua'
OLD = BASE / 'validation-536/startup-candidate/extracted/europe_central_east/war3map.lua'
HARNESS = OUT.parent / 'frozen-startup/probe-lua54-initialization.py'
LIBRARY = BASE / 'validation-536/lua53-runtime/liblua5.3.6-probe.so'
RECEIPT = OUT.parent / 'build-result.json'


def identity(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def literal(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str):
        value = value.encode()
    if isinstance(value, bytes):
        return '"' + ''.join('\\x' + format(byte, '02x') for byte in value) + '"'
    if isinstance(value, list):
        return '{' + ','.join(literal(v) for v in value) + '}'
    if isinstance(value, dict):
        return '{' + ','.join('[' + literal(k) + ']=' + literal(v) for k, v in value.items()) + '}'
    return str(value)


assert not OUT.exists(), 'Preserve previous evidence'
OUT.mkdir()
os.environ['WC3_LUA_PROBE_LIBRARY'] = str(LIBRARY)
spec = importlib.util.spec_from_file_location('frozen_parity_probe', HARNESS)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
lib = module.lib
pointer = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t))(('lua_tolstring', lib))


def get(state, name):
    lib.lua_getglobal(state, name.encode())
    length = ctypes.c_size_t()
    address = pointer(state, -1, ctypes.byref(length))
    assert address, name
    value = ctypes.string_at(address, length.value)
    lib.lua_settop(state, 0)
    return value


SLICE_MODELS = {
    'raw_byte_slices': '',
    'invalid_slice_to_replacement_marker': '''
local rawSlice=SubString
SubString=function(value,first,last)
 local result=rawSlice(value,first,last)
 if utf8.len(result)==nil then return "�" end
 return result
end
''',
}
HASH_MODELS = {
    'all_zero': 'return 0',
    'all_minimum_signed_int': 'return -2147483648',
    'casefold_many_collisions': '''
local first=string.byte(value,1) or 0
if first>=97 and first<=122 then first=first-32 end
return first%3-1
''',
    'stable_casefold_polynomial32': '''
local result=0
for index=1,#value do
 local byte=string.byte(value,index)
 if byte>=97 and byte<=122 then byte=byte-32 end
 result=(result*131+byte)&0xffffffff
end
if result>=0x80000000 then result=result-0x100000000 end
return result
''',
}
COMMON = '''
__wurst_init_bootstrap()
bridge_initCompiletimeState_0()
init_Table("isolated parity table initialization")
init_PlayableCampaignRuntime("isolated parity initialization")
local samples=0
debug.sethook(function()
 samples=samples+10000
 if samples>500000000 then debug.sethook();error("PARITY_SAFETY_BUDGET",0) end
end,"",10000)
function __hex(value)
 return (value:gsub(".",function(char) return string.format("%02x",string.byte(char)) end))
end
'''
EDIT_DRIVER = '''
local output={}
local checks=0
local callsBefore=__probe.nativeCalls.SubString or 0
for _,case in ipairs(__cases) do
 local value=case.document
 for _,op in ipairs(case.operations) do
  value=replaceCampaignField(value,op.key,op.value,"actual archived compiled replacement")
  output[#output+1]=__hex(value)
  if firstAuthorityFieldOffset then
   assert(PlayableCampaignRuntime_indexedAuthority==value,"wrong indexed document")
   local count=0
   for at=1,#value do
    if string.byte(value,at)==59 then
     assert(__wurst_LoadInteger(PlayableCampaignRuntime_authoritySeparators,0,count)==at-1,"wrong cached separator")
     count=count+1
    end
   end
   assert(count==PlayableCampaignRuntime_authoritySeparatorCount,"wrong cached separator count")
   checks=checks+1
  end
 end
end
debug.sethook()
__parity_json=__probe.json({outputs=output,indexChecks=checks,substringCalls=(__probe.nativeCalls.SubString or 0)-callsBefore})
'''
CHECKSUM_DRIVER = '''
local output={}
local distinct={}
local expectedCalls=0
for index,value in ipairs(__values) do
 for at=0,#value-1 do distinct[SubString(value,at,at+1)]=true;expectedCalls=expectedCalls+1 end
 __wurst_stringToIndex("unrelated exact-string identity "..tostring(index))
 output[#output+1]=runtimeChecksum(value,"actual archived checksum")
end
local unique=0
for _ in pairs(distinct) do unique=unique+1 end
debug.sethook()
__parity_json=__probe.json({outputs=output,hashCalls=__hashCalls,uniqueReturnedSlices=unique,
                         bytePositions=expectedCalls,nativeCalls=__probe.nativeCalls})
'''


def execute(script, slice_model, setup, driver):
    state = lib.luaL_newstate()
    assert state
    lib.luaL_openlibs(state)
    try:
        status = lib.luaL_loadfilex(state, str(script).encode(), b't')
        if not status:
            status = lib.lua_pcallk(state, 0, 0, 0, 0, None)
        if status:
            raise RuntimeError(lib.lua_tolstring(state, -1, None).decode(errors='replace'))
        module.execute(state, module.PRELUDE)
        module.execute(state, SLICE_MODELS[slice_model] + COMMON + setup + driver)
        return json.loads(get(state, '__parity_json'))
    finally:
        lib.lua_close(state)


def cases():
    result = []
    documents = [b'', b'v2;map=old;players=origin:a;clock=old', b'v2;x=one;x=two;tail=three',
                 b'v2;trade=v4:cargo;a;store;b;map=next;tail=Z', b'v2;;x=;=empty;;;x;y=weird;x=again;',
                 'v2;名字=玩家;label=München,東京,😀;x=雪;tail=ä'.encode(),
                 b'v2;x=\xff;tail=z;label=\xc3', b'v2;label=\x00\xc3;map=old;x=\xf0\x9f;tail=z']
    for document in documents:
        result.append({'document': document, 'operations': [
            {'key': 'x', 'value': 'a;b=c'}, {'key': 'x', 'value': ''},
            {'key': '名字', 'value': '東京;more=ä'}, {'key': '', 'value': 'empty;'},
            {'key': 'x;y', 'value': 'z;'}, {'key': 'tail', 'value': 'last'},
            {'key': 'bad=key', 'value': 'value'}, {'key': 'map', 'value': 'new'}]})
    rng = random.Random(536438)
    alphabet = ['x', 'y', 'z', ';', '=', ':', '|', '~', ',', 'é', '東', '😀']
    for _ in range(180):
        document = 'v2;' + ''.join(rng.choice(alphabet) for _ in range(rng.randrange(0, 100)))
        operations = []
        for _ in range(6):
            operations.append({'key': rng.choice(['x', 'y', '', 'é', '東', 'x;y', 'bad=key']),
                               'value': ''.join(rng.choice(alphabet) for _ in range(rng.randrange(0, 25)))})
        result.append({'document': document, 'operations': operations})
    return result


report = {
    'format': 'actual_compiled_authority_and_checksum_parity_v1', 'status': 'failed',
    'nativeStatus': 'not_run', 'productionFunctionOverrides': False,
    'limitations': [
        'Both scripts are actual independently extracted compiled archive Lua; no config/main runs in this isolated helper check.',
        'Only explicitly described SubString and StringHash models are supplied. These are stable test oracles, not native Warcraft measurements.',
        'Malformed/partial UTF8 examples test the two explicit slice models. They do not prove all engine normalization behavior.',
        'Each checksum oracle uses a fresh Lua state/cache. Zero, negative and colliding hash values are preserved by exact returned-string identity.',
        'Direct helper differential covers replaceCampaignField. The private removal function is inlined; existing Wurst lifecycle tests cover its callers.',
        'The unchanged observer separately captures actual compiled encode/storage payloads; equality there uses the frozen collision-free hash stub.',
        'The 500M sampled instruction budget per isolated state is a local safety bound, not a Warcraft limit.',
    ],
    'inputs': {name: identity(path) for name, path in {'oldLua': OLD, 'newLua': NEW, 'buildReceipt': RECEIPT,
               'harness': HARNESS, 'library': LIBRARY, 'runner': Path(__file__)}.items()},
    'editModels': [], 'checksumModels': [],
}
began = time.monotonic()
try:
    assert report['inputs']['oldLua']['sha256'] == 'a4fc97bb27b36466bc62bad74605128258c6847c4f46791efe2df184c3f85a45'
    build = json.loads(RECEIPT.read_text())
    assert build['status'] == 'pass' and build['compiledScriptSha256'] == report['inputs']['newLua']['sha256']
    test_cases = cases()
    expected_operations = sum(len(case['operations']) for case in test_cases)
    for slice_model in SLICE_MODELS:
        setup = '__cases=' + literal(test_cases) + '\n'
        old = execute(OLD, slice_model, setup, EDIT_DRIVER)
        new = execute(NEW, slice_model, setup, EDIT_DRIVER)
        assert old['outputs'] == new['outputs']
        assert len(new['outputs']) == new['indexChecks'] == expected_operations
        report['editModels'].append({'sliceModel': slice_model, 'cases': len(test_cases),
                                    'operations': expected_operations, 'cachedIndexesChecked': new['indexChecks'],
                                    'exactOutputBytesEqual': True, 'status': 'pass',
                                    'outputSetSha256': hashlib.sha256(json.dumps(new['outputs'], separators=(',', ':')).encode()).hexdigest()})
    values = [b'', b'aAaA0000||;;==', b'v2;map=west;trade=cargo;hold:grain,2;clock=2|1|0|0|0:1|0',
              'München,東京,😀,ä,é'.encode(), bytes(range(256)) * 4,
              b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', b'\x00' * 32]
    values += values[1:]
    payload = gzip.decompress((OUT.parents[1] / 'startup-observer-collision32/cache-write-1.txt.gz').read_bytes())
    full_body = payload.split(b'|', 1)[1]
    for slice_model in SLICE_MODELS:
        for hash_model, body in HASH_MODELS.items():
            current_values = values + ([full_body] if slice_model == 'raw_byte_slices' and hash_model == 'stable_casefold_polynomial32' else [])
            setup = '__values=' + literal(current_values) + '\n__hashCalls=0\nStringHash=function(value)\nassert(type(value)=="string")\n__hashCalls=__hashCalls+1\n' + body + '\nend\n'
            old = execute(OLD, slice_model, setup, CHECKSUM_DRIVER)
            new = execute(NEW, slice_model, setup, CHECKSUM_DRIVER)
            assert old['outputs'] == new['outputs']
            assert old['hashCalls'] == old['bytePositions']
            assert new['hashCalls'] == new['uniqueReturnedSlices']
            assert all(new['nativeCalls'].get(name, 0) == 0 for name in ('HaveSavedInteger', 'LoadInteger', 'SaveInteger'))
            report['checksumModels'].append({'sliceModel': slice_model, 'hashModel': hash_model,
                'vectors': len(current_values), 'includesFullCapturedBody': len(current_values) > len(values),
                'bytePositions': new['bytePositions'], 'oldHashCalls': old['hashCalls'], 'newHashCalls': new['hashCalls'],
                'uniqueReturnedSlices': new['uniqueReturnedSlices'], 'checksums': new['outputs'],
                'exactChecksumsEqual': True, 'nativeHashtableCalls': 0, 'status': 'pass'})
    actual = NEW.read_text()
    snippets = []
    for name in ('runtimeChecksum', '__wurst_stringToIndex', '__wurst_InitHashtable', '__wurst_SaveInteger',
                 '__wurst_LoadInteger', '__wurst_HaveSavedInteger'):
        match = re.search(r'^function ' + re.escape(name) + r'\(', actual, re.M)
        assert match, name
        end = actual.find('\nfunction ', match.end())
        assert end > match.end()
        snippets.append(actual[match.start():end].rstrip())
    extracted = OUT / 'compiled-checksum-and-table-helpers.lua'
    extracted.write_text('\n\n'.join(snippets) + '\n')
    report['compiledLoweringExcerpt'] = identity(extracted)
    report['fullBody'] = {'bytes': len(full_body), 'sha256': hashlib.sha256(full_body).hexdigest()}
    report['status'] = 'pass_under_explicit_models'
except Exception as error:
    report['error'] = str(error)
    raise
finally:
    report['wallSeconds'] = round(time.monotonic() - began, 6)
    (OUT / 'compiled-parity.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({key: report[key] for key in ('status', 'nativeStatus', 'editModels', 'checksumModels', 'wallSeconds')}, indent=2, sort_keys=True))
