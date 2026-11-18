#!/usr/bin/env python3
"""
build_stress_extra.py — доповнення до stress/ без перезапису наявних шардів.

Створює теку stress-extra/:
  • {перша літера}.json — {слово: [наголоси]} — слова, для яких у stress/ бракує
    варіантів або їх немає зовсім. Клієнт (Редактор поезії) накладає це поверх stress/.
  • _guess.json — модель «за закінченням» для слів, яких немає в жодному словнику.
  • _meta.json — версія, джерела, лічильники.

Джерела:
  1. stress_original.txt (lang-uk/ukrainian-word-stress-dictionary, уже в репозиторії) — усі варіанти
     наголосу з малої літери. Шарди stress/ брали лише ОДИН запис слова, тож губили другий варіант
     омографа (пора́ / по́ра) і подекуди брали наголос власної назви (мені → «Ме́ні»).
  2. СУМ-11 (Словник української мови в 11 т., 1970–1980; суспільне надбання) — DiktJson з
     github.com/bakustarver/ukr-dictionaries-list-opensource (реліз ukr-ukr_SUM-11_or_1).
     Додаються леми, яких немає в stress/, і варіантні наголоси (адже́ / а́дже).
  3. tools/stress-extra-closed.txt — займенники й числівники, яких немає в джерелі 1 (його́, її́, ньо́го…).
  4. Словник Грінченка (1907–1909; суспільне надбання), DiktJson там само (реліз
     ukr-ru_slovar_grinchenka_uaru_dlia_lingvo): наголос позначено великою літерою
     («АбЕтка»). Беруться лише слова, яких немає в джерелах 1–3 (≈5,5 тис. — лексика
     XIX ст., стара орфографія): для класичної й стилізованої поезії.

  З усіх джерел беруться лише факти «слово — місце наголосу».

Запуск з кореня репозиторію (Python 3.9+, лише стандартна бібліотека):
  python tools/build_stress_extra.py --sum path/to/ukr-ukr_SUM-11_or_1.json --grinchenko path/to/ua-ru-hrinchenko.json
Без --sum / --grinchenko — без відповідних джерел.
"""

import argparse, collections, datetime, json, os, re, sys

VOWELS = 'аеєиіїоуюя'
ACUTE = '́'
LETTERS = 'абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'
APOS = re.compile(r"[’ʼ‘`]")


def norm(w: str) -> str:
    return APOS.sub("'", w.strip().lower())


def stresses_of(accented: str):
    """«пора́» → ('пора', [1]); індекс — серед голосних слова"""
    vi, idx, out = -1, [], []
    for ch in accented:
        if ch == ACUTE:
            if vi >= 0 and vi not in idx:
                idx.append(vi)
            continue
        if ch in VOWELS:
            vi += 1
        out.append(ch)
    return ''.join(out), idx


def shard_key(w: str) -> str:
    return ''.join(c for c in w if c in LETTERS)[:2]


def first_letter(w: str) -> str:
    s = ''.join(c for c in w if c in LETTERS)
    return s[:1]


def nvow(w: str) -> int:
    return sum(c in VOWELS for c in w)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--sum', help='СУМ-11 DiktJson (ukr-ukr_SUM-11_or_1.json)')
    ap.add_argument('--grinchenko', help='Словник Грінченка DiktJson (ua-ru-hrinchenko.json)')
    ap.add_argument('--maxn', type=int, default=7, help='найдовше закінчення в моделі')
    ap.add_argument('--holdout', action='store_true', help='оцінити модель на відкладених 10 %% слів')
    a = ap.parse_args()
    root = a.root
    stress_dir = os.path.join(root, 'stress')
    out_dir = os.path.join(root, 'stress-extra')
    os.makedirs(out_dir, exist_ok=True)

    # ── наявні шарди ────────────────────────────────────────────────────
    shards = {}
    for f in os.listdir(stress_dir):
        if f.startswith('_') or not f.endswith('.json'):
            continue
        with open(os.path.join(stress_dir, f), encoding='utf8') as fh:
            shards[f[:-5]] = json.load(fh)

    def in_shards(w):
        return shards.get(shard_key(w), {}).get(w)

    extra = {}
    counts = collections.Counter()

    # ── 1. усі варіанти з малої літери з stress_original.txt ──────────────
    lower = collections.OrderedDict()
    with open(os.path.join(root, 'stress_original.txt'), encoding='utf8') as fh:
        for line in fh:
            line = line.strip()
            if not line or ' ' in line or ACUTE not in line or not line[0].islower():
                continue
            w, idx = stresses_of(norm(line))
            if not idx:
                continue
            cur = lower.setdefault(w, [])
            for i in idx:
                if i not in cur:
                    cur.append(i)
    for w, idx in lower.items():
        s = in_shards(w)
        if s is None:
            continue
        if set(s) != set(idx):
            extra[w] = idx
            counts['source-variants'] += 1

    # ── 2. СУМ-11 ─────────────────────────────────────────────────────────
    if a.sum:
        with open(a.sum, encoding='utf8') as fh:
            d = json.load(fh)
        for k, v in d.items():
            if k.startswith('##'):
                continue
            for b in re.findall(r'<b>([^<]+)</b>', v)[:3]:
                b = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]', '', b).strip().rstrip(',.;:').strip()
                b = norm(b)
                if ACUTE not in b or ' ' in b:
                    continue
                w, idx = stresses_of(b)
                if not idx or not re.fullmatch(r"[а-яіїєґ'-]+", w) or nvow(w) < 2 or max(idx) >= nvow(w):
                    continue
                base = extra.get(w) or in_shards(w)
                if base is None:
                    extra[w] = idx
                    counts['sum11-new'] += 1
                elif not set(idx) <= set(base):
                    extra[w] = list(base) + [i for i in idx if i not in base]
                    counts['sum11-variants'] += 1

    # ── 3. займенники й числівники ───────────────────────────────────────
    closed = collections.OrderedDict()
    with open(os.path.join(root, 'tools', 'stress-extra-closed.txt'), encoding='utf8') as fh:
        for line in fh:
            line = line.split('#', 1)[0].strip()
            for form in line.split():
                w, idx = stresses_of(norm(form))
                cur = closed.setdefault(w, [])
                cur += [i for i in idx if i not in cur]
    for w, idx in closed.items():
        if not idx:
            continue
        # Вичитаний вручну список має перевагу: у джерелі для цих форм трапляються
        # діалектні чи інших слів наголоси («йо́го»), а шард подекуди взяв власну назву.
        # Справжні омографи перелічено в рядку списку («сорока́ соро́ка»).
        cur = extra.get(w) or in_shards(w)
        if cur is None or list(cur) != idx:
            extra[w] = idx
            counts['closed-class'] += 1

    # ── 4. Грінченко: лише слова, яких ніде немає ────────────────────────
    if a.grinchenko:
        upper = VOWELS.upper()
        with open(a.grinchenko, encoding='utf8') as fh:
            d = json.load(fh)
        for k, v in d.items():
            if k.startswith('##'):
                continue
            m = re.match(r'<div><b>([^<]+)</b>', v)
            if not m:
                continue
            for h in re.split(r',\s*', m.group(1)):
                h = h.strip().rstrip('.!?')
                if not re.fullmatch(r"[А-ЯІЇЄҐа-яіїєґ'’-]+", h) or h.startswith('-') or len(h) < 2:
                    continue
                # перша літера завжди велика; наголос — велика голосна далі;
                # «ААкати» — подвоєна перша голосна означає наголос на ній
                marks = [i for i, c in enumerate(h) if i > 0 and c in upper]
                if not marks:
                    continue
                w = norm(h)
                if nvow(w) < 2:
                    continue
                if h[0] in upper and h[1] in upper:
                    idx = [0]
                else:
                    idx = sorted({nvow(w[:p]) for p in marks})
                if w in extra or in_shards(w) is not None or w in lower:
                    continue
                extra[w] = idx
                counts['grinchenko-new'] += 1

    # ── запис шарів ───────────────────────────────────────────────────────
    by_letter = collections.defaultdict(dict)
    for w, idx in extra.items():
        by_letter[first_letter(w)][w] = idx
    for f in os.listdir(out_dir):
        if f.endswith('.json') and not f.startswith('_'):
            os.remove(os.path.join(out_dir, f))
    for L, m in by_letter.items():
        with open(os.path.join(out_dir, f'{L}.json'), 'w', encoding='utf8') as fh:
            json.dump(dict(sorted(m.items())), fh, ensure_ascii=False, separators=(',', ':'))

    # ── модель «за закінченням» ───────────────────────────────────────────
    words = []
    for sh in shards.values():
        for w, idx in sh.items():
            if len(idx) != 1:
                continue
            n = nvow(w)
            if n < 2 or idx[0] >= n:
                continue
            words.append((w.replace("'", ''), n - 1 - idx[0]))  # позиція від кінця; без апострофа — як у редакторі
    if a.holdout:
        import zlib
        test = [x for x in words if zlib.crc32(x[0][:5].encode()) % 10 == 0]
        train = [x for x in words if zlib.crc32(x[0][:5].encode()) % 10 != 0]
    else:
        test, train = [], words
    model, n_entries = build_model(train, a.maxn)
    with open(os.path.join(out_dir, '_guess.json'), 'w', encoding='utf8') as fh:
        json.dump(model, fh, ensure_ascii=False, separators=(',', ':'))
    if test:
        tab = {}
        for key, sufs in model['t'].items():
            for s in sufs.split(' '):
                tab[(key[0], key[1], s)] = key[2:]
        ok1 = ok2 = 0
        for w, s in test:
            c = predict(tab, w, a.maxn)
            ok1 += c[0] == s
            ok2 += s in c[:2]
        print(f'модель: точність {ok1 / len(test):.4f}, у двох кандидатах {ok2 / len(test):.4f}; '
              f'передостанній склад: {sum(s == 1 for _, s in test) / len(test):.4f} ({len(test)} слів)')

    meta = {
        'v': 1,
        'generated': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'letters': sorted(by_letter),
        'words': len(extra),
        'counts': counts,
        'guess': {'entries': n_entries, 'maxn': a.maxn, 'trainWords': len(train)},
        'sources': [
            'lang-uk/ukrainian-word-stress-dictionary (stress_original.txt) — усі варіанти',
            'СУМ-11 (1970–1980), DiktJson bakustarver/ukr-dictionaries-list-opensource' if a.sum else None,
            'tools/stress-extra-closed.txt — займенники й числівники',
            'Б. Грінченко, Словарь української мови (1907–1909), DiktJson bakustarver/ukr-dictionaries-list-opensource' if a.grinchenko else None,
        ],
    }
    meta['sources'] = [s for s in meta['sources'] if s]
    with open(os.path.join(out_dir, '_meta.json'), 'w', encoding='utf8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print(json.dumps({'words': len(extra), **counts, 'guessEntries': n_entries}, ensure_ascii=False))


def model_key(w, n):
    return ('1' if w.startswith('ви') else '0') + str(min(n, 5))


def build_model(train, maxn, minc=5, second_share=0.3):
    """Суфіксна модель: для (префікс «ви-», к-сть складів, закінчення) — найчастіша позиція наголосу
    від кінця і, якщо помітна, друга. Зберігаються лише вузли, що відрізняються від коротшого закінчення."""
    cnt = collections.defaultdict(collections.Counter)
    for w, s in train:
        k0 = model_key(w, nvow(w))
        for k in range(1, maxn + 1):
            if k > len(w):
                break
            cnt[(k0, w[-k:])][s] += 1
    eff = {}
    keep = {}
    for key in sorted(cnt, key=lambda x: len(x[1])):
        k0, suf = key
        c = cnt[key]
        tot = sum(c.values())
        parent = eff.get((k0, suf[1:]), '1')
        if tot >= minc:
            mc = c.most_common(2)
            val = str(mc[0][0])
            if len(mc) > 1 and mc[1][1] / tot >= second_share:
                val += '/' + str(mc[1][0])
            eff[key] = val
            if val != parent:
                keep[key] = val
        else:
            eff[key] = parent
    groups = collections.defaultdict(list)
    for (k0, suf), val in keep.items():
        groups[k0 + val].append(suf)
    return {'v': 1, 'maxn': maxn, 't': {k: ' '.join(sorted(v)) for k, v in sorted(groups.items())}}, len(keep)


def predict(tab, w, maxn):
    k0 = model_key(w, nvow(w))
    for k in range(min(maxn, len(w)), 0, -1):
        v = tab.get((k0[0], k0[1], w[-k:]))
        if v is not None:
            return [int(x) for x in v.split('/')]
    return [1]


if __name__ == '__main__':
    sys.exit(main())
