# Studio library and media refresh

The root library combines all entries exposed by the existing 3D viewer, the
recent-result projection catalog, all local MP4s (including previously unlisted
variants), and the image archive. Counts refer to display entries, not distinct
accepted simulations. Historical, partial, and bounded-result labels remain
separate. The original landing page remains at `archive.html`.

`build_studio_catalog.cjs` uses existing catalogs only. Run it after adding display
assets, then run `check_studio_catalog.cjs` to verify IDs, file coverage and links.
The site needs only static hosting; no solver, AI schedule, or backend is started.

`add_plm_display.py` adds only the previously missing accepted HLLC/PLM control:
11 edge-on + 11 face-on projections and 21 3D meshes. New sample masses and times
are compared to its saved accepted reductions. It does not rerun evolution or
the completed validator. See `plm_display_audit.json`. The older HLLE cooling-on
catalog field is corrected from `none` to `tabular`, supported by its bound
`input.in` (`enable_cooling = tabular`). No numerical fields are changed.

`prepare_studio_media.py` creates two 1920×1080 H.264 MP4s for each recent run.
Each contains 11 actual saved projections held for two seconds, in a 30 fps
container. Spatial resampling is a display choice; no new temporal fluid motion
is inferred. Original native resolution remains documented in the catalog.
Legacy movies retain their original encoded streams and timing; where necessary,
the MP4 seek index is moved to the front for progressive playback. All original
movie versions remain available through version selection and Git history.
The original checkout and raw simulation files are untouched.

Media generation uses one encoder thread and local D: outputs. Python dependencies
and workspace paths in the export scripts are local bindings and should be
adapted on other computers. No C: cleanup, reservation changes, or simulation
controller changes are part of this update.

The library supports combined search/filters, favorites saved only in the browser,
shareable film links, compact/card layouts, and explicit load-more pagination.
Films have rate, loop, picture-in-picture and download controls. Recent comparison
links preserve the selected runs, projection and sampled time. The 3D viewer has
search, playback-rate selection and safer keyboard handling in form controls.
