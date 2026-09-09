# Third-party software and scientific references

Cloud Studio is Kaan Boge's project. Its original viewer, presentation and
specified utilities are distinct from the independently developed native
simulation packages used to generate results. See [LICENSING.md](LICENSING.md).

## Bundled browser dependency

`vendor/three.module.js` identifies **three.js r160**, copyright 2010–2023
Three.js Authors, SPDX MIT. `vendor/addons/controls/OrbitControls.js` is the
three.js camera-control addon. Their upstream license is included unmodified
in [vendor/LICENSE.threejs](vendor/LICENSE.threejs).

Source and license: [three.js r160](https://github.com/mrdoob/three.js/tree/r160),
[upstream LICENSE](https://github.com/mrdoob/three.js/blob/r160/LICENSE).
The original copyright header is retained. These files are not credited as
software written by Kaan Boge.

## Native simulation packages and analysis dependencies

AthenaPK, Athena++, Athena 4.2, Enzo, Enzo-E, RAMSES, FLASH 4.8, Flash-X, Arepo,
GIZMO, Gadget-4 and Gasoline retain their upstream licenses and access terms.
The same applies to externally installed yt, NumPy, SciPy, matplotlib,
scikit-image, h5py, ffmpeg and parallel runtimes. These are not relicensed by
Cloud Studio's root LICENSE.

The `code/` exports and native-source adaptations in `analysis/` are outside
the new MIT grant. Their existing notices and provenance are preserved. This
document is not a certification that every historical excerpt has complete
redistribution documentation.

## Scientific references and records

References in the methods, reports and scripts identify published scientific
work. They are not project coauthor labels. Original dated analyses and source
evidence are retained as records of the work performed, including the context
of scientific feedback. This presentation update does not rewrite them or
assign another researcher's contributions to Kaan Boge.
