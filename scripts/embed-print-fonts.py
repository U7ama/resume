"""Embed the licensed print fonts so every device uses the same PDF metrics."""
import base64
from pathlib import Path

root = Path(__file__).resolve().parents[1]
start = '/* BEGIN EMBEDDED PRINT FONTS */'
end = '/* END EMBEDDED PRINT FONTS */'
license_text = (root / 'assets/fonts/OFL.txt').read_text()
rules = [start, '/*\n' + license_text + '*/']
for style, weight in [('Regular', 400), ('Bold', 700)]:
    encoded = base64.b64encode((root / f'assets/fonts/ResumePrint-{style}.woff2').read_bytes()).decode()
    rules.append('@font-face { font-family: "Resume Print"; font-style: normal; '
                 f'font-weight: {weight}; font-display: block; '
                 f'src: url("data:font/woff2;base64,{encoded}") format("woff2"); }}')
rules.append(end)
css = root / 'studio.css'
text = css.read_text()
if start in text:
    text = text.split(end, 1)[1].lstrip('\n')
css.write_text('\n'.join(rules) + '\n' + text)
print('Embedded regular and bold print fonts with their license.')
