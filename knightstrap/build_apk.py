#!/usr/bin/env python3
"""
Knight's Trap — APK Build Script
==================================
Run this once on your PC:   python build_apk.py

It will:
  1. Download Three.js r149 (last version before UMD deprecation)
  2. Download OrbitControls for r149
  3. Inline both into knights_trap_apk.html
  4. Write knights_trap_FINAL.html — fully self-contained, zero CDN dependencies

Then use knights_trap_FINAL.html in MIT App Inventor.
"""

import urllib.request
import os
import sys

THREE_URL   = "https://cdn.jsdelivr.net/npm/three@0.149.0/build/three.min.js"
INPUT_FILE  = "knights_trap_apk.html"
OUTPUT_FILE = "knights_trap_FINAL.html"

# OrbitControls path varies by CDN mirror — try several
ORBIT_URLS = [
    "https://unpkg.com/three@0.149.0/examples/js/controls/OrbitControls.js",
    "https://cdn.jsdelivr.net/npm/three@0.149.0/examples/js/controls/OrbitControls.js",
    "https://unpkg.com/three@0.148.0/examples/js/controls/OrbitControls.js",
    "https://cdn.jsdelivr.net/npm/three@0.148.0/examples/js/controls/OrbitControls.js",
    "https://unpkg.com/three@0.147.0/examples/js/controls/OrbitControls.js",
]

def download(url, label):
    print(f"  Downloading {label}...", end=" ", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read().decode("utf-8")
        print(f"OK ({len(data)//1024} KB)")
        return data
    except Exception as e:
        print(f"FAILED ({e})")
        return None

def download_orbit():
    print("  Fetching OrbitControls (trying multiple sources):")
    for url in ORBIT_URLS:
        # Show a short label derived from the URL
        label = url.replace("https://", "").split("/examples")[0]
        print(f"    {label}...", end=" ", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read().decode("utf-8")
            print(f"OK ({len(data)//1024} KB)")
            return data
        except Exception as e:
            print(f"failed ({e})")
    return None

def build():
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: '{INPUT_FILE}' not found.")
        print(f"  Make sure this script is in the same folder as {INPUT_FILE}")
        sys.exit(1)

    print("Knight's Trap — APK Builder")
    print("=" * 40)

    three_js = download(THREE_URL, "Three.js r149")
    if not three_js:
        print("\nERROR: Could not download Three.js. Check your internet connection.")
        sys.exit(1)

    orbit_js = download_orbit()
    if not orbit_js:
        print()
        print("ERROR: Could not download OrbitControls from any source.")
        print()
        print("Manual fallback:")
        print("  Open this URL in your browser and save the page as 'OrbitControls.js'")
        print("  in the same folder as this script:")
        print("  https://unpkg.com/three@0.149.0/examples/js/controls/OrbitControls.js")
        print()
        print("  Then re-run:  python build_apk.py")
        sys.exit(1)

    print(f"  Reading {INPUT_FILE}...", end=" ", flush=True)
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        html = f.read()
    print("OK")

    # Replace the CDN/shim block with fully inlined scripts
    old_block = """<!-- ES Module Shims: polyfills importmap + ES modules for older Android WebViews -->
<script async src="https://cdn.jsdelivr.net/npm/es-module-shims@1.8.3/dist/es-module-shims.js"></script>
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }
}
</script>
<script type="module-shim">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';"""

    new_block = f"""<!-- Three.js + OrbitControls — fully inlined, zero CDN dependencies -->
<script>
{three_js}
</script>
<script>
{orbit_js}
</script>
<script>
/* THREE and THREE.OrbitControls are now available as globals */"""

    if old_block not in html:
        print("\nERROR: Could not find the expected script block in the HTML.")
        print("  The HTML may have been manually edited since it was generated.")
        sys.exit(1)

    html = html.replace(old_block, new_block)

    # Fix OrbitControls constructor — UMD build attaches it to THREE
    html = html.replace(
        "const controls = new OrbitControls(camera, renderer.domElement);",
        "const controls = new THREE.OrbitControls(camera, renderer.domElement);"
    )

    print(f"  Writing {OUTPUT_FILE}...", end=" ", flush=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = os.path.getsize(OUTPUT_FILE) // 1024
    print(f"OK ({size_kb} KB)")

    print()
    print("=" * 40)
    print(f"SUCCESS!  '{OUTPUT_FILE}' is ready.")
    print()
    print("Next steps:")
    print("  1. Go to appinventor.mit.edu and open your project")
    print("  2. Click 'Add File' (top menu) and upload knights_trap_FINAL.html")
    print("  3. In the Blocks editor, on Screen1.Initialize:")
    print('       WebViewer.LoadURL  ->  "file:///android_asset/knights_trap_FINAL.html"')
    print("  4. Build > Export APK")
    print()
    print("The game is fully offline — no internet needed on the tablet.")

if __name__ == "__main__":
    build()
