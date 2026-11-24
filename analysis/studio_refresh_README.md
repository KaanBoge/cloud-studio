# Studio library and media

The library combines the complete runs, the earlier runs in the 3D viewer, the films and the image
archive. The original landing page remains at `archive.html`.

## Complete runs

Every complete run has all 101 saved states, from t = 0 to 5 t<sub>cc</sub>. Its files live on the `runs`
branch, one folder per run id, and each catalog entry points at its folder through the `base` field:

* `edge.png` and `face.png`: column density pictures, one 128 pixel row per saved state.
* `poster-edge.jpg` and `poster-face.jpg`: the last saved state, at 5 t<sub>cc</sub>.
* `film-edge.mp4` and `film-face.mp4`: 1920 × 1080 H.264 films at 60 fps. Each saved state appears on
  its own frame, 240 frames per t<sub>cc</sub>, with linear cross fades between neighbouring states. The
  first state is held for 0.5 s and the last for 1 s.
* `3d/index.json` and `3d/fNNN.bin`: two density surfaces per state (0.15 and 0.6 of the initial cloud
  density) for the 3D viewer.
* `entry.json` and `entry3d.json`: the catalog entries.

The tools in `run_staging/` made these folders. `build_studio_catalog.cjs` builds the library catalog
from the display catalogs; `check_studio_catalog.cjs --base-root <runs branch checkout>` then verifies
ids, file coverage, surfaces and links. The site needs only static hosting.

## Earlier media

`add_plm_display.py`, `prepare_studio_media.py`, `build_60fps.py`, `fix_60fps_labels.py` and
`package_60fps.py` made the earlier displays with eleven states per run and their 60 fps previews on the
`media-60fps` branch. The complete runs replace those displays; the films of the archive keep their
60 fps previews. On 24 November 2026 `build_60fps.py` rebuilt those 442 previews with a new footer line
and `package_60fps_batches.py` committed them to `media-60fps` in batches of at most 128 MiB.

The library supports search and filters, favourites saved only in the browser, shareable film links and
compact or card layouts. Films have rate, loop, picture in picture and download controls.
