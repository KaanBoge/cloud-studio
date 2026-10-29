New 3D gallery: 16 retained native evolutions, 21 real saved states per run (336 meshes). Source receipts and actual timestamps are recorded in each index.

Rendering: total gas density divided by initial cloud density; surfaces at 0.15 and 0.6; Gaussian sigma 0.8 native cells, marching-cubes step 2, 16-bit quantized vertices, smooth interpolated normals. These are lossy display products, not analysis fields. Native data and accepted scalar reductions are unchanged. Particle volumes use cell-deposited mass divided by volume with periodic display smoothing. No temporal interpolation or inferred fluid motion.

All new exports passed sampled mass/dense-mass comparison and binary-layout checks. Separate visual PNG, orbit video and evolution video checks passed. Matching displayed levels do not certify matched physics, convergence or accuracy. Existing old runs remain accessible.

Local export script is retained with its original research-workspace bindings; adapt paths and scientific Python dependencies for another machine. It reuses the read-only grid readers in recent_gallery_export.py without modifying that source.
