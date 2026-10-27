"""Publish only the public resume files, never runtime configuration or history."""
from pathlib import Path
import shutil

FILES = ['index.html', 'studio.js', 'studio.css', 'resume.md', 'academic.md', 'general.md',
         'portfolio.md',
         'Usama DP.jpeg', 'Usama DP headshot.jpeg', 'robots.txt', 'sitemap.xml']


def main():
    root = Path(__file__).resolve().parents[1]
    destination = root / 'output/pages'
    destination.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copyfile(root / name, destination / name)
    print('Packaged public CV templates and assets only.')


if __name__ == '__main__':
    main()
