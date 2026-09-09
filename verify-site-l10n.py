#!/usr/bin/env python3
"""Bilingual website guard. No network; run before publishing the site.

The site is two copies of the same markup with the text swapped, so the
failure mode is not a broken page — it is a page that looks finished and has
an English paragraph in the middle of it. That is what this looks for.
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent
PAIRS = [('index.html', 'ar/index.html'), ('privacy.html', 'ar/privacy.html'),
         ('terms.html', 'ar/terms.html'), ('contact.html', 'ar/contact.html'),
         ('404.html', 'ar/404.html')]

# Latin that legitimately survives translation: the brand, proper nouns, the
# package id, licence names, and addresses.
ALLOWED = {
    'SalahNow', 'Salah', 'Now', 'Valeed', 'Labs', 'Ummer', 'Parachikkottil',
    'Google', 'Play', 'Android', 'Tanzil', 'Project', 'GeoNames', 'Creative',
    'Commons', 'Attribution', 'INTERNET', 'English', 'com', 'valeedlabs',
    'salahnow', 'salahnowapp', 'gmail', 'com', 'tanzil', 'net', 'github',
    'https', 'Foundation', 'Furqaan', 'Drive', 'ID',
}

def text_nodes(src):
    body = re.search(r'<body.*?</body>', src, re.S)
    if not body:
        return []
    b = re.sub(r'<(script|style|template)\b.*?</\1>', '', body.group(0), flags=re.S)
    return [m.group(1).strip() for m in re.finditer(r'>([^<>]+)<', b)
            if m.group(1).strip()]

def main():
    problems = []
    for en_name, ar_name in PAIRS:
        en = ROOT / en_name
        ar = ROOT / ar_name
        if not ar.exists():
            problems.append(f'{ar_name} is missing'); continue
        ar_src = ar.read_text(encoding='utf-8')
        en_src = en.read_text(encoding='utf-8')

        if 'lang="ar"' not in ar_src or 'dir="rtl"' not in ar_src:
            problems.append(f'{ar_name}: not declared as Arabic right-to-left')
        if 'lang="en"' not in en_src:
            problems.append(f'{en_name}: not declared as English')

        # The two pages must be the same page, not two different designs.
        def tags(s):
            body = re.search(r'<body.*?</body>', s, re.S).group(0)
            # The authoritative-language notice is the ONE element the Arabic
            # legal pages carry and the English ones do not. It is deliberate
            # — an Arabic reader has to be told which text governs — so it is
            # excluded here rather than allowed to hide a real divergence.
            body = re.sub(r'<p class="note".*?</p>', '', body, flags=re.S)
            return re.findall(r'<(\w+)', body)
        if tags(en_src) != tags(ar_src):
            problems.append(
                f'{ar_name}: markup differs from {en_name} — the Arabic site '
                f'must be the same page, not a second design')

        # A translated legal page must say which language governs.
        if ar_name in ('ar/privacy.html', 'ar/terms.html'):
            if 'النص الإنجليزي هو المرجع' not in ar_src:
                problems.append(
                    f'{ar_name}: no authoritative-language notice. A courtesy '
                    f'translation of a legal text must say so.')

        # Physical CSS directions break RTL silently.
        # Text and box spacing must mirror. Absolute POSITIONING is left out
        # on purpose: a centred decoration uses `left:50%` with a transform,
        # which is direction-neutral, and rewriting it as a logical property
        # actively broke the hero arc in Arabic.
        for prop in ('text-align:left', 'text-align:right',
                     'margin-left:', 'margin-right:',
                     'padding-left:', 'padding-right:',
                     'border-left:', 'border-right:'):
            if prop in ar_src.replace(' ', ''):
                problems.append(f'{ar_name}: physical CSS "{prop}" — use a '
                                f'logical property so RTL mirrors')

        # English prose left in an Arabic page.
        words = re.compile(r'\b[A-Za-z][A-Za-z\'’]{2,}\b')
        for node in text_nodes(ar_src):
            stray = [w for w in words.findall(node) if w not in ALLOWED]
            if len(stray) >= 3:
                problems.append(
                    f'{ar_name}: English left in "{node[:60]}" ({stray[:4]})')

        # An Arabic page showing English app screenshots is the "translated,
        # not designed" failure in picture form. The Arabic captures live
        # beside the page, so the Arabic homepage must not reach up a level
        # for them.
        if ar_name == 'ar/index.html':
            for shot in ('prayer-times', 'qibla', 'tracker', 'quran'):
                if f'src="../{shot}.png"' in ar_src:
                    problems.append(
                        f'{ar_name}: uses the English {shot}.png')
                if not (ROOT / 'ar' / f'{shot}.png').exists():
                    problems.append(f'ar/{shot}.png is missing')

        # Both directions of the language switch, on both pages.
        for name, src in ((en_name, en_src), (ar_name, ar_src)):
            if name.endswith('404.html'):
                continue  # a 404 has no stable twin to point at
            if 'hreflang="ar"' not in src or 'hreflang="en"' not in src:
                problems.append(f'{name}: no language switch')
            if 'rel="canonical"' not in src:
                problems.append(f'{name}: no canonical URL')

    for p in problems:
        print('FAIL', p)
    print(f'\n{len(PAIRS)} page pairs · {len(problems)} problems')
    return len(problems)

if __name__ == '__main__':
    sys.exit(min(main(), 250))
