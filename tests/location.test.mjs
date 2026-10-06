import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../web/src/location.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { requestLocation } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);

test('position provider is called only on request, returns coordinates and accuracy', async () => {
  let calls = 0;
  const provider = { getCurrentPosition(success, failure, options) {
    calls++;
    assert.equal(options.timeout, 15000);
    assert.equal(options.maximumAge, 0);
    success({ coords: { latitude: 24, longitude: 121, accuracy: 25 } });
  } };
  assert.equal(calls, 0);
  assert.deepEqual(await requestLocation(provider), {latitude:24,longitude:121,accuracy:25});
  assert.equal(calls, 1);
});
test('permission denial, timeout and unavailable have actionable messages', async () => {
  for (const [code, text] of [[1,/權限/],[2,/無法取得/],[3,/逾時/]]) {
    await assert.rejects(requestLocation({getCurrentPosition(success, failure) {failure({code});}}),text);
  }
});
test('invalid coordinate does not produce a map position', async () => {
  await assert.rejects(requestLocation({getCurrentPosition(success) {success({coords:{latitude:91,longitude:121,accuracy:20}});}}),/無效/);
});
test('unsupported browser has a clear error', async () => {
  await assert.rejects(requestLocation(null),/不支援定位/);
});
