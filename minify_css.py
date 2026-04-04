#!/usr/bin/env python3
"""Minify CSS assets for production builds."""
import csscompressor
import os

def minify_css():
    src = os.path.join(os.path.dirname(__file__), 'wwwroot', 'css', 'styles.css')
    dst = os.path.join(os.path.dirname(__file__), 'wwwroot', 'css', 'styles.min.css')

    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()

    minified = csscompressor.compress(content)

    with open(dst, 'w', encoding='utf-8') as f:
        f.write(minified)

    src_size = os.path.getsize(src)
    dst_size = len(minified.encode('utf-8'))
    print(f"CSS minified: {src_size} → {dst_size} bytes ({100 * dst_size // src_size}% of original)")

if __name__ == '__main__':
    minify_css()
