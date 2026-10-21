import argparse
import hashlib
import json
import pathlib
import re
import sys

STAGES = ['brief', 'story', 'director', 'assets', 'animation', 'edit', 'sound', 'review', 'delivery']
MODES = {'plan': STAGES[:3], 'review': ['review'], 'revise': STAGES, 'production': STAGES}
class Invalid(ValueError):
    pass

def check(ok, message):
    if not ok:
        raise Invalid(message)

def obj(v, fields):
    check(type(v) is dict and set(v) == set(fields.split()), 'incorrect or unknown fields: ' + fields)

def ident(v):
    check(type(v) is str and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', v), 'invalid identifier')

def digest(v):
    check(type(v) is str and re.fullmatch('[a-f0-9]{64}', v), 'invalid SHA-256')

def refs(v, known):
    check(type(v) is list and all(type(x) is str for x in v), 'expected string references')
    check(len(v) == len(set(v)) and set(v) <= known, 'duplicate or unknown reference')

def file_record(v):
    obj(v, 'path sha256'); p = v['path']
    check(type(p) is str and p and '\\' not in p and '\x00' not in p, 'invalid relative path')
    check(not pathlib.PurePosixPath(p).is_absolute() and all(x not in ('', '.', '..') for x in p.split('/')), 'unsafe relative path')
    digest(v['sha256'])

def unique(rows):
    check(type(rows) is list and len(rows) <= 10000, 'expected bounded list')
    seen = set()
    for row in rows:
        check(type(row) is dict and 'id' in row, 'missing id'); ident(row['id'])
        check(row['id'] not in seen, 'duplicate id'); seen.add(row['id'])
    return seen

def scope(doc, row):
    by_id = {a['id']: a for a in doc['artifacts']}
    seen = set(); todo = list(row['artifact_ids'])
    while todo:
        aid = todo.pop()
        if aid not in seen:
            seen.add(aid); todo.extend(by_id[aid]['dependencies'])
    binding = {'project_id': doc['project_id'], 'mode': doc['mode'], 'author_id': doc['author_id'],
               'obligation': {k: v for k, v in row.items() if k not in ('evidence', 'scope_sha256')},
               'artifacts': sorted((by_id[x] for x in seen), key=lambda a: a['id'])}
    return hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def validate(doc):
    obj(doc, 'schema_version project_id mode author_id artifacts actions reviews')
    check(type(doc['schema_version']) is int and doc['schema_version'] == 1, 'unsupported schema version')
    ident(doc['project_id']); ident(doc['author_id'])
    check(type(doc['mode']) is str and doc['mode'] in MODES, 'unsupported mode')
    aids = unique(doc['artifacts']); check(aids, 'at least one artifact required')
    for a in doc['artifacts']:
        obj(a, 'id path sha256 dependencies'); file_record({k: a[k] for k in ('path', 'sha256')}); refs(a['dependencies'], aids)
    remaining = {a['id']: set(a['dependencies']) for a in doc['artifacts']}
    while remaining:
        ready = {k for k, v in remaining.items() if not v}; check(ready, 'cyclic artifact dependencies')
        remaining = {k: v - ready for k, v in remaining.items() if k not in ready}
    unique(doc['actions']); unique(doc['reviews'])
    check({a.get('kind') for a in doc['actions'] if type(a.get('kind')) is str} == set(MODES[doc['mode']]), 'mode requires all and only allowed action kinds')
    for group in ('actions', 'reviews'):
        for row in doc[group]:
            obj(row, 'id artifact_ids status evidence scope_sha256 ' + ('kind' if group == 'actions' else 'reviewer_id'))
            refs(row['artifact_ids'], aids); check(row['artifact_ids'], 'obligation needs artifacts')
            check(type(row['status']) is str and row['status'] in (('pending', 'done') if group == 'actions' else ('pending', 'pass', 'fail')), 'invalid status')
            if group == 'actions':
                check(type(row['kind']) is str and row['kind'] in MODES[doc['mode']], 'action forbidden in mode')
            else:
                ident(row['reviewer_id']); check(row['reviewer_id'] != doc['author_id'], 'reviewer must differ from author')
            if row['status'] == 'pending':
                check(row['evidence'] is None and row['scope_sha256'] is None, 'pending obligation cannot claim evidence')
            else:
                file_record(row['evidence']); digest(row['scope_sha256'])
                check(row['scope_sha256'] == scope(doc, row), 'stale scope binding: ' + row['id'])
    if doc['mode'] != 'plan':
        check({x for r in doc['reviews'] for x in r['artifact_ids']} == aids, 'every artifact needs an explicit review obligation')
    return doc

def checked_file(root, record):
    # The caller-selected root may have an OS alias; compare canonical paths.
    # Relative components beneath this root must still never be symlinks.
    root = root.resolve(strict=True)
    check(root.is_dir(), "manifest root is not a directory")
    candidate = root
    for component in record['path'].split('/'):
        candidate = candidate / component; check(not candidate.is_symlink(), 'symlink forbidden: ' + record['path'])
    check(candidate.resolve().is_relative_to(root), 'path escapes manifest directory')
    check(candidate.is_file(), 'missing regular file: ' + record['path'])
    h = hashlib.sha256()
    with candidate.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    check(h.hexdigest() == record['sha256'], 'hash mismatch: ' + record['path'])

def verify(doc, root):
    for a in doc['artifacts']: checked_file(root, a)
    for group in ('actions', 'reviews'):
        for row in doc[group]:
            if row['evidence'] is not None: checked_file(root, row['evidence'])

def next_step(doc):
    for row in doc['reviews']:
        if row['status'] == 'fail': return {'state': 'REVIEW_FAILED' if doc['mode'] in ('review', 'plan') else 'REPAIR_REQUIRED', 'id': row['id']}
    for stage in MODES[doc['mode']]:
        for row in doc['actions']:
            if row['kind'] == stage and row['status'] != 'done': return {'state': 'ACTION_REQUIRED', 'id': row['id'], 'kind': stage}
    for row in doc['reviews']:
        if row['status'] != 'pass': return {'state': 'REVIEW_REQUIRED', 'id': row['id']}
    return {'state': 'RECORDED_OBLIGATIONS_COMPLETE', 'warning': 'Recorded integrity only; not artistic quality, authentic reviewer identity, rights, delivery accessibility or publication proof.'}

def no_duplicates(pairs):
    result = {}
    for k, v in pairs:
        check(k not in result, 'duplicate JSON key: ' + k); result[k] = v
    return result

def main():
    parser = argparse.ArgumentParser(description='Offline evidence checker: no rendering, uploads or spending.')
    parser.add_argument('command', choices=['validate', 'verify', 'next']); parser.add_argument('manifest', type=pathlib.Path)
    args = parser.parse_args()
    try:
        check(args.manifest.stat().st_size <= 4 * 1024 * 1024, 'manifest exceeds 4 MiB')
        check(not args.manifest.is_symlink(), 'manifest symlink forbidden')
        doc = validate(json.loads(args.manifest.read_text(encoding='utf-8'), object_pairs_hook=no_duplicates))
        if args.command != 'validate': verify(doc, args.manifest.resolve().parent)
        print(json.dumps(next_step(doc) if args.command == 'next' else {'state': 'VALID_STRUCTURE' if args.command == 'validate' else 'VERIFIED_BYTES', 'quality_verified': False}))
        return 0
    except (Invalid, OSError, ValueError, TypeError, KeyError, RecursionError, OverflowError) as exc:
        print(json.dumps({'state': 'ERROR', 'message': str(exc)}), file=sys.stderr); return 2

if __name__ == '__main__': sys.exit(main())
